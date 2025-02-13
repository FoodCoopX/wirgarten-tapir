from datetime import date, datetime
from decimal import Decimal
from typing import List

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.db.models import (
    Subquery,
    OuterRef,
    Sum,
    F,
    DecimalField,
    ExpressionWrapper,
    Case,
    When,
    FloatField,
)
from django.db.models.functions import Coalesce
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import (
    CoopShareTransaction,
    MandateReference,
    Member,
    MemberPickupLocation,
    Payment,
    PickupLocation,
    ReceivedCoopSharesLogEntry,
    Subscription,
    TransferCoopSharesLogEntry,
    WaitingListEntry,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import (
    generate_future_deliveries,
    get_next_delivery_date,
)
from tapir.wirgarten.service.email import send_email
from tapir.wirgarten.service.payment import generate_mandate_ref
from tapir.wirgarten.service.products import (
    get_future_subscriptions,
    get_active_subscriptions,
)
from tapir.wirgarten.service.tasks import schedule_task_unique
from tapir.wirgarten.tapirmail import Events
from tapir.wirgarten.tasks import send_email_member_contract_end_reminder
from tapir.wirgarten.utils import (
    format_date,
    format_subscription_list_html,
    get_now,
    get_today,
)


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

    origin_member = Member.objects.get(id=origin_member_id)
    origin_ownerships_quantity = origin_member.coop_shares_quantity

    if origin_ownerships_quantity is None or quantity < 1:
        return False  # nothing to do

    # if quantity exceeds origin shares, just take all shares
    if quantity > origin_ownerships_quantity:
        quantity = origin_ownerships_quantity

    today = get_today()
    new_ownership = CoopShareTransaction.objects.create(
        member_id=target_member_id,
        quantity=quantity,
        share_price=settings.COOP_SHARE_PRICE,
        valid_at=today,
        transaction_type=CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN,
        transfer_member_id=origin_member_id,
    )

    CoopShareTransaction.objects.create(
        member_id=origin_member_id,
        quantity=-quantity,
        share_price=settings.COOP_SHARE_PRICE,
        valid_at=today,
        transaction_type=CoopShareTransaction.CoopShareTransactionType.TRANSFER_OUT,
        transfer_member_id=target_member_id,
    )

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

    # generate member no
    Member.objects.get(id=target_member_id).save()


def cancel_coop_shares(
    member: str | Member,
    quantity: int,
    cancellation_date: datetime | date,
    valid_at: date,
):
    member_id = resolve_member_id(member)

    CoopShareTransaction.objects.create(
        member_id=member_id,
        quantity=-quantity,
        share_price=settings.COOP_SHARE_PRICE,
        valid_at=valid_at,
        timestamp=cancellation_date,
        transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
    )


def create_mandate_ref(member: str | Member):
    """
    Generates and persists a new mandate reference for a member.

    :param member: the member
    """

    member_id = resolve_member_id(member)
    ref = generate_mandate_ref(member_id)
    return MandateReference.objects.create(
        ref=ref, member_id=member_id, start_ts=get_now()
    )


def resolve_member_id(member: str | Member | TapirUser) -> str:
    return member.id if type(member) is not str and member.id else member


def get_or_create_mandate_ref(member: str | Member) -> MandateReference:
    """
    Returns the existing mandate ref for a member of creates a new one if none exists.
    """

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
        mandate_ref = create_mandate_ref(member_id)

    return mandate_ref


def get_next_contract_start_date(ref_date: date = None):
    """
    Gets the next start date for a contract. Usually the first of the next month.

    :param ref_date: the reference date
    :return: the next contract start date
    """
    if ref_date is None:
        ref_date = get_today()

    now = ref_date
    y, m = divmod(now.year * 12 + now.month, 12)
    return date(y, m + 1, 1)


@transaction.atomic
def buy_cooperative_shares(
    quantity: int,
    member: int | str | Member,
    start_date: date = None,
    mandate_ref: MandateReference = None,
):
    """
    Member buys cooperative shares. The start date is the date on which the member enters the cooperative (after the trial period).

    :param quantity: how many coop shares to buy
    :param member: the member
    :param start_date: the date on which the member officially enters the cooperative
    """
    member_id = resolve_member_id(member)

    if start_date == None:
        start_date = get_next_contract_start_date()

    if mandate_ref is None:
        mandate_ref = get_or_create_mandate_ref(member_id)

    share_price = settings.COOP_SHARE_PRICE
    due_date = start_date + relativedelta(
        day=get_parameter_value(Parameter.PAYMENT_DUE_DAY)
    )
    if due_date < start_date:
        due_date = due_date + relativedelta(months=1)

    payment_type = "Genossenschaftsanteile"
    existing_payment = Payment.objects.filter(
        due_date=due_date,
        mandate_ref=mandate_ref,
        status=Payment.PaymentStatus.DUE,
        type=payment_type,
    )
    if existing_payment.exists():
        payment = existing_payment.first()
        payment.amount = float(payment.amount) + share_price * quantity
        payment.save()
    else:
        payment = Payment.objects.create(
            due_date=due_date,
            amount=share_price * quantity,
            mandate_ref=mandate_ref,
            status=Payment.PaymentStatus.DUE,
            type=payment_type,
        )

    coop_share_tx = CoopShareTransaction.objects.create(
        member_id=member_id,
        quantity=quantity,
        share_price=share_price,
        valid_at=start_date,
        mandate_ref=mandate_ref,
        transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        payment=payment,
    )

    member = Member.objects.get(id=member_id)
    member.sepa_consent = get_now()
    member.save()

    return coop_share_tx


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

    try:
        member = Member.objects.get(email=email)
    except Member.DoesNotExist:
        member = None

    return WaitingListEntry.objects.create(
        first_name=first_name,
        last_name=last_name,
        email=email,
        privacy_consent=get_now(),
        type=type,
        member=member,
    )


@transaction.atomic
def change_pickup_location(
    member_id: str, new_pickup_location: PickupLocation, change_date: date
):
    """
    Changes the pickup location of a member at the specified change_date.

    1. Deletes all MemberPickupLocations with valid_from date >= change_date
    2. Creates a new MemberPickupLocations with valid_from = change_date

    :param member_id: the member id
    :param new_pickup_location: the new pickup location
    :param change_date: the date at which the new pickup locations becomes active
    :return:
    """

    MemberPickupLocation.objects.filter(
        member_id=member_id, valid_from__gte=change_date
    ).delete()
    MemberPickupLocation.objects.create(
        member_id=member_id,
        pickup_location_id=new_pickup_location.id,
        valid_from=change_date,
    )


def get_next_trial_end_date(sub: Subscription = None):
    return (
        sub.trial_end_date
        if sub
        else (get_today() + relativedelta(day=1, months=1, days=-1))
    )


def get_subscriptions_in_trial_period(member: int | str | Member):
    member_id = resolve_member_id(member)
    today = get_today()
    min_start_date = today + relativedelta(day=1, months=-1)

    subs = get_active_subscriptions().filter(
        member_id=member_id,
        cancellation_ts__isnull=True,
        start_date__gte=min_start_date,
        end_date__gt=today,
    )

    return subs.filter(id__in=[sub.id for sub in subs if sub.trial_end_date > today])


def send_cancellation_confirmation_email(
    member: str | Member,
    contract_end_date: date,
    subs_to_cancel: List[Subscription],
    revoke_coop_membership: bool = False,
    skip_email: bool = False,
):
    member_id = resolve_member_id(member)
    member = Member.objects.get(pk=member_id)

    contract_list = f"{'<br/>'.join(map(lambda x: '- ' + str(x), subs_to_cancel))}"
    if revoke_coop_membership:
        contract_list += "\n- Beitrittserklärung zur Genossenschaft"

    future_subs = get_future_subscriptions(
        contract_end_date + relativedelta(days=1)
    ).filter(member_id=member_id)
    if (
        not future_subs.exists()
    ):  # only schedule contract end reminder if the member has no other contracts left
        schedule_task_unique(
            task=send_email_member_contract_end_reminder,
            eta=contract_end_date,
            kwargs={"member_id": member_id},
        )

    future_deliveries = generate_future_deliveries(member)

    last_pickup_date = "Letzte Abholung schon vergangen"
    if len(future_deliveries) > 0:
        last_pickup_date = format_date(
            datetime.strptime(future_deliveries[-1]["delivery_date"], "%Y-%m-%d").date()
        )

    TransactionalTrigger.fire_action(
        Events.TRIAL_CANCELLATION,
        member.email,
        {
            "contract_list": contract_list,
            "contract_end_date": format_date(contract_end_date),
            "last_pickup_date": last_pickup_date,
        },
    )

    if not skip_email:
        # TODO: remove this once migrated to mail module
        send_email(
            to_email=[member.email],
            subject=get_parameter_value(
                Parameter.EMAIL_CANCELLATION_CONFIRMATION_SUBJECT
            ),
            content=get_parameter_value(
                Parameter.EMAIL_CANCELLATION_CONFIRMATION_CONTENT
            ),
            variables={
                "contract_end_date": format_date(contract_end_date),
                "contract_list": contract_list,
            },
        )


def send_contract_change_confirmation(member: Member, subs: List[Subscription]):
    if not len(subs):
        raise Exception(
            "No subscriptions provided for sending contract change confirmation for member: ",
            member,
        )

    contract_start_date = subs[0].start_date

    future_deliveries = generate_future_deliveries(member)

    send_email(
        to_email=[member.email],
        subject=get_parameter_value(
            Parameter.EMAIL_CONTRACT_CHANGE_CONFIRMATION_SUBJECT
        ),
        content=get_parameter_value(
            Parameter.EMAIL_CONTRACT_CHANGE_CONFIRMATION_CONTENT
        ),
        variables={
            "contract_start_date": format_date(contract_start_date),
            "contract_end_date": format_date(subs[0].end_date),
            "first_pickup_date": format_date(
                get_next_delivery_date(contract_start_date)
            ),
            "contract_list": f"{'<br/>'.join(map(lambda x: '- ' + x.long_str(), subs))}",
        },
    )

    TransactionalTrigger.fire_action(
        Events.MEMBERAREA_CHANGE_CONTRACT,
        member.email,
        {
            "contract_start_date": format_date(contract_start_date),
            "contract_end_date": format_date(subs[0].end_date),
            "first_pickup_date": format_date(
                get_next_delivery_date(contract_start_date)
            ),
            "contract_list": format_subscription_list_html(subs),
        },
    )

    last_delivery_date = datetime.strptime(
        future_deliveries[-1]["delivery_date"], "%Y-%m-%d"
    ).date()

    schedule_task_unique(
        task=send_email_member_contract_end_reminder,
        eta=last_delivery_date + relativedelta(days=1),
        kwargs={"member_id": member.id},
    )


def send_order_confirmation(member: Member, subs: List[Subscription]):
    if not len(subs):
        raise Exception(
            "No subscriptions provided for sending order confirmation for member: ",
            member,
        )

    contract_start_date = subs[0].start_date

    future_deliveries = generate_future_deliveries(member)
    send_email(
        to_email=[member.email],
        subject=get_parameter_value(
            Parameter.EMAIL_CONTRACT_ORDER_CONFIRMATION_SUBJECT
        ),
        content=get_parameter_value(
            Parameter.EMAIL_CONTRACT_ORDER_CONFIRMATION_CONTENT
        ),
        variables={
            "contract_start_date": format_date(contract_start_date),
            "contract_end_date": format_date(subs[0].end_date),
            "first_pickup_date": future_deliveries[0]["delivery_date"],
            "contract_list": f"{'<br/>'.join(map(lambda x: '- ' + x.long_str(), subs))}",
        },
    )

    TransactionalTrigger.fire_action(
        Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION,
        member.email,
        {
            "contract_start_date": format_date(contract_start_date),
            "contract_end_date": format_date(subs[0].end_date),
            "first_pickup_date": future_deliveries[0]["delivery_date"],
            "contract_list": format_subscription_list_html(subs),
        },
    )

    last_delivery_date = datetime.strptime(
        future_deliveries[-1]["delivery_date"], "%Y-%m-%d"
    ).date()

    schedule_task_unique(
        task=send_email_member_contract_end_reminder,
        eta=last_delivery_date + relativedelta(days=1),
        kwargs={"member_id": member.id},
    )


def annotate_member_queryset_with_coop_shares_total_value(queryset, outer_ref="id"):
    today = get_today()
    overnext_month = today + relativedelta(months=2)

    return queryset.annotate(
        coop_shares_total_value=Coalesce(
            Subquery(
                CoopShareTransaction.objects.filter(
                    member_id=OuterRef(outer_ref),
                    valid_at__lte=overnext_month,
                    # I do this to include new members in the list, which will join the coop soon
                )
                .values("member_id")
                .annotate(total_value=Sum(F("quantity") * F("share_price")))
                .values("total_value"),
                output_field=DecimalField(),
            ),
            Decimal(0.0),
        )
    )


def annotate_member_queryset_with_monthly_payment(queryset):
    today = get_today()

    active_subscriptions_per_member = Subscription.objects.filter(
        member_id=OuterRef("id"),
        start_date__lte=today,
        end_date__gte=today,
        product__productprice__valid_from__lte=today,
    )

    subscriptions_with_monthly_payment = active_subscriptions_per_member.annotate(
        monthly_payment=ExpressionWrapper(
            Case(
                When(
                    solidarity_price_absolute__isnull=True,
                    then=(
                        F("product__productprice__price")
                        * F("quantity")
                        * (1 + F("solidarity_price"))
                    ),
                ),
                When(
                    solidarity_price_absolute__isnull=False,
                    then=(
                        (F("product__productprice__price") * F("quantity"))
                        + F("solidarity_price_absolute")
                    ),
                ),
                default=0.0,
                output_field=FloatField(),
            ),
            output_field=FloatField(),
        )
    )

    return queryset.annotate(
        monthly_payment=Coalesce(
            Subquery(
                subscriptions_with_monthly_payment.values("member_id")
                .annotate(total=Sum("monthly_payment"))
                .values("total"),
                output_field=FloatField(),
            ),
            0,
            output_field=FloatField(),
        )
    )
