from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Sum

from tapir.accounts.models import TapirUser, LdapPerson
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import (
    ShareOwnership,
    TransferCoopSharesLogEntry,
    MandateReference,
    Member,
    ReceivedCoopSharesLogEntry,
    Payment,
    WaitingListEntry,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.payment import generate_mandate_ref
from tapir.wirgarten.service.products import get_future_subscriptions


@transaction.atomic
def transfer_coop_shares(
    origin_member_id, target_member_id, quantity: int, actor: TapirUser
):
    """
    Transfer cooperative shares from one member to another. Payment for this transfer is not handled by Tapir.

    :param origin_member_id: the id of the origin Member/TapirUser
    :param target_member_id: the id of the target Member/TapirUser
    :param quantity: how many share to transfer
    :param actor: who initiated the transfer (admin account)
    """

    origin_ownerships = ShareOwnership.objects.filter(
        member_id=origin_member_id
    ).order_by("-created_at")
    origin_ownerships_quantity = origin_ownerships.aggregate(sum=Sum("quantity"))["sum"]

    if quantity < 1:
        return False  # nothing to do

    # if quantity exceeds origin shares, just take all shares
    if quantity > origin_ownerships_quantity:
        quantity = origin_ownerships_quantity

    try:
        existing_ownership = ShareOwnership.objects.get(member_id=target_member_id)
        mandate_ref = existing_ownership.mandate_ref
    except ShareOwnership.DoesNotExist:
        mandate_ref = create_mandate_ref(target_member_id, True)

    actual_coop_start = get_next_contract_start_date(
        date.today() + relativedelta(months=1)
    )
    new_ownership = ShareOwnership.objects.create(
        member_id=target_member_id,
        quantity=quantity,
        share_price=get_parameter_value(Parameter.COOP_SHARE_PRICE),
        entry_date=actual_coop_start,
        mandate_ref=mandate_ref,
    )

    # TODO: can we delete the ShareOwnership if quantity == 0 ?
    quantity_to_transfer = quantity
    while quantity_to_transfer > 0:
        for oo in origin_ownerships:
            if quantity_to_transfer < 1:
                break
            delta = min(quantity_to_transfer, oo.quantity)
            oo.quantity -= delta
            oo.save()
            quantity_to_transfer -= delta

    origin_member = Member.objects.get(pk=origin_member_id)

    # log entry for the user who SOLD the shares
    TransferCoopSharesLogEntry().populate(
        actor=actor,
        user=origin_member,
        target_member=new_ownership.member,
        quantity=quantity,
    ).save()

    # log entry for the user who RECEIVED the shares
    ReceivedCoopSharesLogEntry().populate(
        actor=actor,
        user=new_ownership.member,
        target_member=origin_member,
        quantity=quantity,
    ).save()


def create_mandate_ref(member: int | str | Member, coop_shares: bool):
    """
    Generates and persists a new mandate reference for a member.

    :param member: the member
    :param coop_shares: if true: the mandate ref is generated for coop shares, else: generated for products
    """

    member_id = resolve_member_id(member)
    ref = generate_mandate_ref(member_id, coop_shares)
    return MandateReference.objects.create(
        ref=ref, member_id=member_id, start_ts=datetime.now()
    )


def resolve_member_id(member):
    return member.id if type(member) is Member else member


def get_or_create_mandate_ref(
    member: int | str | Member, coop_shares: bool
) -> MandateReference:
    member_id = member.id if type(member) is Member else member

    if coop_shares:
        raise NotImplementedError("Coop share mandate references can not be reused.")

    mandate_ref = False
    for row in (
        get_future_subscriptions()
        .filter(member_id=member_id)
        .order_by("-start_date")
        .values("mandate_ref")[:1]
    ):
        mandate_ref = MandateReference.objects.get(ref=row["mandate_ref"])
        break

    if not mandate_ref:
        mandate_ref = create_mandate_ref(member_id, False)

    return mandate_ref


@transaction.atomic
def create_member(member: Member):
    """
    Persists the given member instance together with the necessary Ldap objects.

    :param member: the new member instance
    """

    if not member.username:
        # FIXME: this leads to duplicate usernames (see #8)
        member.username = member.first_name.lower() + "." + member.last_name.lower()

    if member.has_ldap():
        ldap_user = member.get_ldap()
    else:
        ldap_user = LdapPerson(uid=member.username)

    ldap_user.sn = member.last_name or member.username
    ldap_user.cn = member.get_full_name() or member.username
    ldap_user.mail = member.email
    ldap_user.save()

    member.save()
    return member


def get_next_contract_start_date(ref_date=date.today()):
    """
    Gets the next start date for a contract. Usually the first of the next month.

    :param ref_date: the reference date
    :return: the next contract start date
    """

    now = ref_date
    y, m = divmod(now.year * 12 + now.month, 12)
    return date(y, m + 1, 1)


@transaction.atomic
def buy_cooperative_shares(
    quantity: int,
    member: int | str | Member,
    start_date: date = get_next_contract_start_date(),
):
    """
    Member buys cooperative shares. The start date is the date on which the member enters the cooperative (after the trial period).

    :param quantity: how many coop shares to buy
    :param member: the member
    :param start_date: the date on which the member officially enters the cooperative
    """

    member_id = resolve_member_id(member)

    share_price = get_parameter_value(Parameter.COOP_SHARE_PRICE)
    due_date = start_date.replace(day=get_parameter_value(Parameter.PAYMENT_DUE_DAY))

    mandate_ref = create_mandate_ref(member_id, True)
    so = ShareOwnership.objects.create(
        member_id=member_id,
        quantity=quantity,
        share_price=share_price,
        entry_date=start_date,
        mandate_ref=mandate_ref,
    )

    Payment.objects.create(
        due_date=due_date,
        amount=share_price * quantity,
        mandate_ref=so.mandate_ref,
        status=Payment.PaymentStatus.DUE,
    )


def create_wait_list_entry(
    first_name: str, last_name: str, email: str, type: WaitingListEntry.WaitingListType
):
    """
    Create a wait list entry for a non-member.

    :param first_name: the first name of the interested person
    :param last_name: the last name of the interested person
    :param email: the contact email address
    :return: the newly created WaitListEntry
    """
    return WaitingListEntry.objects.create(
        first_name=first_name,
        last_name=last_name,
        email=email,
        privacy_consent=datetime.now(),
        type=type,
    )
