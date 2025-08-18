import datetime
from decimal import Decimal
from typing import List, Dict

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.db.models import (
    Subquery,
    OuterRef,
    Sum,
    F,
    DecimalField,
    FloatField,
)
from django.db.models.functions import Coalesce
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import TapirUser
from tapir.coop.services.membership_text_service import MembershipTextService
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    CoopShareTransaction,
    MandateReference,
    Member,
    MemberPickupLocation,
    PickupLocation,
    ReceivedCoopSharesLogEntry,
    Subscription,
    TransferCoopSharesLogEntry,
    WaitingListEntry,
    GrowingPeriod,
)
from tapir.wirgarten.service.delivery import (
    get_next_delivery_date,
)
from tapir.wirgarten.service.payment import generate_mandate_ref
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.service.subscriptions import (
    annotate_subscriptions_queryset_with_monthly_payment_including_solidarity,
)
from tapir.wirgarten.service.tasks import schedule_task_unique
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
    cancellation_date: datetime.datetime | datetime.date,
    valid_at: datetime.date,
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


def create_mandate_ref(member: str | Member, cache: Dict | None = None):
    """
    Generates and persists a new mandate reference for a member.

    :param member: the member
    """

    member_id = resolve_member_id(member)
    ref = generate_mandate_ref(member_id)
    return MandateReference.objects.create(
        ref=ref, member_id=member_id, start_ts=get_now(cache)
    )


def resolve_member_id(member: str | Member | TapirUser) -> str:
    return member.id if type(member) is not str and member.id else member


le_sum = 0


def get_or_create_mandate_ref(
    member: str | Member,
    cache: Dict | None = None,
) -> MandateReference:
    """
    Returns the existing mandate ref for a member of creates a new one if none exists.
    """

    member_id = resolve_member_id(member)

    def compute():
        return {
            mandate_ref.member_id: mandate_ref
            for mandate_ref in MandateReference.objects.all()
        }

    mandate_ref_cache = get_from_cache_or_compute(cache, "mandate_ref_cache", compute)
    mandate_ref = mandate_ref_cache.get(member_id, None)
    if mandate_ref:
        return mandate_ref

    mandate_ref = create_mandate_ref(member_id, cache)
    if mandate_ref_cache:
        mandate_ref_cache[member_id] = mandate_ref
    return mandate_ref


def create_wait_list_entry(
    member: Member | None,
    first_name: str,
    last_name: str,
    email: str,
    phone_number: str,
    street: str,
    street_2: str,
    postcode: str,
    city: str,
):
    return WaitingListEntry.objects.create(
        member=member,
        first_name=first_name,
        last_name=last_name,
        email=email,
        privacy_consent=get_now(),
        phone_number=phone_number,
        street=street,
        street_2=street_2,
        postcode=postcode,
        city=city,
        country="DE",
        comment="",
        number_of_coop_shares=0,
    )


@transaction.atomic
def change_pickup_location(
    member_id: str, new_pickup_location: PickupLocation, change_date: datetime.date
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


def send_cancellation_confirmation_email(
    member: str | Member,
    contract_end_date: datetime.date,
    subs_to_cancel: List[Subscription],
    revoke_coop_membership: bool = False,
    cache: Dict = None,
):
    member_id = resolve_member_id(member)
    member = Member.objects.get(pk=member_id)

    contract_list = f"{'<br/>'.join(map(lambda x: '- ' + str(x), subs_to_cancel))}"
    if revoke_coop_membership:
        contract_list += "\n- " + MembershipTextService.get_membership_text(cache=cache)

    future_subs = get_active_and_future_subscriptions(
        contract_end_date + relativedelta(days=1), cache=cache
    ).filter(member_id=member_id)
    if (
        not future_subs.exists()
    ):  # only schedule contract end reminder if the member has no other contracts left
        schedule_task_unique(
            task=send_email_member_contract_end_reminder,
            eta=contract_end_date,
            kwargs={"member_id": member_id},
        )

    end_date = GrowingPeriod.objects.order_by("end_date").last().end_date
    future_deliveries = GetDeliveriesService.get_deliveries(
        member=member, date_from=get_today(cache=cache), date_to=end_date, cache=cache
    )

    last_pickup_date = "Letzte Abholung schon vergangen"
    if len(future_deliveries) > 0:
        last_pickup_date = format_date(future_deliveries[-1]["delivery_date"])

    TransactionalTrigger.fire_action(
        TransactionalTriggerData(
            key=Events.TRIAL_CANCELLATION,
            recipient_id_in_base_queryset=member.id,
            token_data={
                "contract_list": contract_list,
                "contract_end_date": format_date(contract_end_date),
                "last_pickup_date": last_pickup_date,
            },
        ),
    )


def send_contract_change_confirmation(
    member: Member, subs: List[Subscription], cache: Dict
):
    if not len(subs):
        raise Exception(
            "No subscriptions provided for sending contract change confirmation for member: ",
            member,
        )

    contract_start_date = subs[0].start_date

    end_date = GrowingPeriod.objects.order_by("end_date").last().end_date
    for subscription in subs:
        if subscription.end_date:
            end_date = min(subscription.end_date, end_date)
    future_deliveries = GetDeliveriesService.get_deliveries(
        member=member, date_from=get_today(cache=cache), date_to=end_date, cache=cache
    )

    TransactionalTrigger.fire_action(
        TransactionalTriggerData(
            key=Events.MEMBERAREA_CHANGE_CONTRACT,
            recipient_id_in_base_queryset=member.id,
            token_data={
                "contract_start_date": format_date(contract_start_date),
                "contract_end_date": format_date(subs[0].end_date),
                "first_pickup_date": format_date(
                    get_next_delivery_date(contract_start_date, cache=cache)
                ),
                "contract_list": format_subscription_list_html(subs),
            },
        ),
    )

    last_delivery_date = future_deliveries[-1]["delivery_date"]

    schedule_task_unique(
        task=send_email_member_contract_end_reminder,
        eta=datetime.datetime.combine(
            last_delivery_date + relativedelta(days=1), datetime.time()
        ),
        kwargs={"member_id": member.id},
    )


def send_order_confirmation(
    member: Member, subs: List[Subscription], cache: Dict, from_waiting_list: bool
):
    if len(subs) == 0:
        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=Events.REGISTER_MEMBERSHIP_ONLY,
                recipient_id_in_base_queryset=member.id,
            ),
        )
        return

    min_contract_start_date = min([subscription.start_date for subscription in subs])
    min_contract_end_date = min([subscription.end_date for subscription in subs])

    first_pickup_date = datetime.date(year=datetime.MAXYEAR, month=12, day=31)
    at_least_one_product_with_delivery = False
    for subscription in subs:
        if subscription.product.type.delivery_cycle == NO_DELIVERY[0]:
            continue
        at_least_one_product_with_delivery = True
        next_delivery_date = DeliveryDateCalculator.get_next_delivery_date_for_delivery_cycle(
            reference_date=subscription.start_date,
            pickup_location_id=MemberPickupLocationService.get_member_pickup_location_id(
                member, subscription.start_date
            ),
            delivery_cycle=subscription.product.type.delivery_cycle,
            cache=cache,
        )
        first_pickup_date = min(first_pickup_date, next_delivery_date)

    TransactionalTrigger.fire_action(
        TransactionalTriggerData(
            key=(
                Events.WAITING_LIST_ORDER_CONFIRMATION
                if from_waiting_list
                else Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION
            ),
            recipient_id_in_base_queryset=member.id,
            token_data={
                "contract_start_date": format_date(min_contract_start_date),
                "contract_end_date": format_date(min_contract_end_date),
                "first_pickup_date": (
                    format_date(first_pickup_date)
                    if at_least_one_product_with_delivery
                    else "Keine Lieferung"
                ),
                "contract_list": format_subscription_list_html(list(subs)),
            },
        ),
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


def annotate_member_queryset_with_monthly_payment(
    queryset, reference_date: datetime.date
):
    active_subscriptions_per_member = Subscription.objects.filter(
        member_id=OuterRef("id"),
        start_date__lte=reference_date,
        end_date__gte=reference_date,
    )

    active_subscriptions_per_member = (
        annotate_subscriptions_queryset_with_monthly_payment_including_solidarity(
            active_subscriptions_per_member, reference_date
        ).distinct()
    )

    return queryset.annotate(
        monthly_payment=Coalesce(
            Subquery(
                active_subscriptions_per_member.values("member_id")
                .annotate(total=Sum("monthly_payment"))
                .values("total"),
                output_field=FloatField(),
            ),
            0,
            output_field=FloatField(),
        )
    )
