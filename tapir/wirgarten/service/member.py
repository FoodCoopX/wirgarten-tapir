from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from django.db import transaction

from tapir.accounts.models import TapirUser, LdapPerson
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import (
    ShareOwnership,
    TransferCoopSharesLogEntry,
    MandateReference,
    Member,
    ReceivedCoopSharesLogEntry,
    Payment,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.payment import generate_mandate_ref


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

    origin_ownership = ShareOwnership.objects.get(member_id=origin_member_id)

    if quantity < 1:
        return False  # nothing to do

    # if quantity exceeds origin shares, just take all shares
    if quantity > origin_ownership.quantity:
        quantity = origin_ownership.quantity

    try:
        target_ownership = ShareOwnership.objects.get(member_id=target_member_id)
        target_ownership.quantity += quantity
        target_ownership.save()
    except ShareOwnership.DoesNotExist:
        mandate_ref = create_mandate_ref(target_member_id, True)
        actual_coop_start = get_next_contract_start_date(
            date.today() + relativedelta(months=1)
        )
        target_ownership = ShareOwnership.objects.create(
            member_id=target_member_id,
            quantity=quantity,
            share_price=origin_ownership.share_price,
            entry_date=actual_coop_start,
            mandate_ref=mandate_ref,
        )

    # TODO: can we delete the ShareOwnership if quantity == 0 ?
    origin_ownership.quantity -= quantity
    origin_ownership.save()

    # log entry for the user who SOLD the shares
    TransferCoopSharesLogEntry().populate(
        actor=actor,
        user=origin_ownership.member,
        target_member=target_ownership.member,
        quantity=quantity,
    ).save()

    # log entry for the user who RECEIVED the shares
    ReceivedCoopSharesLogEntry().populate(
        actor=actor,
        user=target_ownership.member,
        target_member=origin_ownership.member,
        quantity=quantity,
    ).save()


def create_mandate_ref(member: int | str | Member, coop_shares: bool):
    """
    Generates and persists a new mandate reference for a member.

    :param member: the member
    :param coop_shares: if true: the mandate ref is generated for coop shares, else: generated for products
    """

    member_id = member.id if type(member) is Member else member
    ref = generate_mandate_ref(member_id, coop_shares)
    return MandateReference.objects.create(
        ref=ref, member_id=member_id, start_ts=datetime.now()
    )


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
    quantity: int, member: Member, start_date: date = get_next_contract_start_date()
):
    """
    Member buys cooperative shares. The start date is the date on which the member enters the cooperative (after the trial period).

    :param quantity: how many coop shares to buy
    :param member: the member
    :param start_date: the date on which the member officially enters the cooperative
    """

    share_price = get_parameter_value(Parameter.COOP_SHARE_PRICE)
    due_date = start_date.replace(day=get_parameter_value(Parameter.PAYMENT_DUE_DAY))

    try:
        so = ShareOwnership.objects.get(member=member)
        so.quantity += quantity
        so.save()
    except ShareOwnership.DoesNotExist:
        mandate_ref = create_mandate_ref(member, True)
        so = ShareOwnership.objects.create(
            member=member,
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
