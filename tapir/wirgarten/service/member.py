from datetime import date, datetime, timezone

from dateutil.relativedelta import relativedelta
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Sum

from tapir import settings
from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import (
    ShareOwnership,
    TransferCoopSharesLogEntry,
    MandateReference,
    Member,
    ReceivedCoopSharesLogEntry,
    Payment,
    WaitingListEntry,
    Subscription,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.service.payment import generate_mandate_ref
from tapir.wirgarten.service.products import get_future_subscriptions
from tapir.wirgarten.tasks import send_email_member_contract_end_reminder
from tapir.wirgarten.utils import format_date


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

    mandate_ref = create_mandate_ref(target_member_id, True)

    actual_coop_start = get_next_contract_start_date(
        date.today() + relativedelta(months=1)
    )
    new_ownership = ShareOwnership.objects.create(
        member_id=target_member_id,
        quantity=quantity,
        share_price=settings.COOP_SHARE_PRICE,
        entry_date=actual_coop_start,
        mandate_ref=mandate_ref,
    )

    quantity_to_transfer = quantity
    for oo in origin_ownerships:
        if quantity_to_transfer < 1:
            break
        delta = min(quantity_to_transfer, oo.quantity)
        oo.quantity -= delta
        quantity_to_transfer -= delta
        oo.save()

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


def create_mandate_ref(member: str | Member, coop_shares: bool):
    """
    Generates and persists a new mandate reference for a member.

    :param member: the member
    :param coop_shares: if true: the mandate ref is generated for coop shares, else: generated for products
    """

    member_id = resolve_member_id(member)
    ref = generate_mandate_ref(member_id, coop_shares)
    return MandateReference.objects.create(
        ref=ref, member_id=member_id, start_ts=datetime.now(timezone.utc)
    )


def resolve_member_id(member: str | Member | TapirUser) -> str:
    return member.id if type(member) is not str and member.id else member


def get_or_create_mandate_ref(
    member: str | Member, coop_shares: bool = False
) -> MandateReference:
    if coop_shares:
        raise NotImplementedError("Coop share mandate references can not be reused.")

    member_id = resolve_member_id(member)
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

    share_price = settings.COOP_SHARE_PRICE
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


def get_next_trial_end_date(sub: Subscription = None):
    return (
        (sub.start_date if sub else date.today()) + relativedelta(day=1, months=1)
    ) + relativedelta(days=-1)


def get_subscriptions_in_trial_period(member: int | str | Member):
    member_id = resolve_member_id(member)
    today = date.today()
    min_start_date = today + relativedelta(day=1, months=-1)

    return get_future_subscriptions().filter(
        member_id=member_id,
        cancellation_ts__isnull=True,
        start_date__gt=min_start_date,
    )


def send_cancellation_confirmation_email(
    member: str | Member, contract_end_date: date, subs_to_cancel: [Subscription]
):
    member_id = resolve_member_id(member)
    member = Member.objects.get(pk=member_id)
    email = EmailMultiAlternatives(
        subject=get_parameter_value(Parameter.EMAIL_CANCELLATION_CONFIRMATION_SUBJECT),
        body=get_parameter_value(
            Parameter.EMAIL_CANCELLATION_CONFIRMATION_CONTENT
        ).format(
            member=member,
            contract_end_date=format_date(contract_end_date),
            admin_name=get_parameter_value(Parameter.SITE_ADMIN_NAME),
            site_name=get_parameter_value(Parameter.SITE_NAME),
            contract_list=f"{'<br/>'.join(map(lambda x: '- ' + str(x), subs_to_cancel))}<br/>",
        ),
        to=[member.email],
        from_email=settings.EMAIL_HOST_SENDER,
    )
    email.content_subtype = "html"
    email.send()

    send_email_member_contract_end_reminder.apply_async(
        eta=contract_end_date, args=[member_id]
    )

    # TODO: Log entry!


def send_order_confirmation(member: Member, subs: [Subscription]):
    if not len(subs):
        raise Exception(
            "No subscriptions provided for sending order confirmation for member: ",
            member,
        )

    contract_start_date = subs[0].start_date
    email = EmailMultiAlternatives(
        subject=get_parameter_value(
            Parameter.EMAIL_CONTRACT_ORDER_CONFIRMATION_SUBJECT
        ),
        body=get_parameter_value(
            Parameter.EMAIL_CONTRACT_ORDER_CONFIRMATION_CONTENT
        ).format(
            member=member,
            contract_start_date=format_date(contract_start_date),
            contract_end_date=format_date(subs[0].end_date),
            first_pickup_date=format_date(get_next_delivery_date(contract_start_date)),
            admin_name=get_parameter_value(Parameter.SITE_ADMIN_NAME),
            site_name=get_parameter_value(Parameter.SITE_NAME),
            contract_list=f"{'<br/>'.join(map(lambda x: '- ' + str(x), subs))}<br/>",
        ),
        to=[member.email],
        from_email=settings.EMAIL_HOST_SENDER,
    )
    email.content_subtype = "html"
    email.send()
