import datetime
import logging
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.utils.shortcuts import get_any_element_from_set
from tapir.wirgarten.models import Member, Payment, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys

logger = logging.getLogger(__name__)


class MissingPickupLocationError(ValueError):
    """
    Raised when a member has a billable delivery on a date but no pickup
    location assigned on that date - an invalid state we cannot bill for.
    """


class MonthPaymentBuilderDeliveryCharges:
    PAYMENT_TYPE_DELIVERY_CHARGE = "payment_type_delivery_charge"

    @classmethod
    def build_payments_for_delivery_charges(
        cls,
        current_month: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
        in_trial: bool,
    ) -> list[Payment]:
        target_month = current_month
        if in_trial:
            target_month = (target_month - relativedelta(months=1)).replace(day=1)

        subscriptions = (
            MonthPaymentBuilderSubscriptions.get_current_and_renewed_subscriptions(
                cache=cache, first_of_month=target_month, is_in_trial=in_trial
            )
        )

        subscriptions_by_member = cls._group_subscriptions_by_member(subscriptions)

        payments_to_create = []
        for member, member_subscriptions in subscriptions_by_member.items():
            if in_trial:
                rhythm = MemberPaymentRhythm.Rhythm.MONTHLY.value
            else:
                rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                    member=member, reference_date=target_month, cache=cache
                )

            try:
                payments_to_create.extend(
                    cls.build_payments_for_member(
                        member=member,
                        contracts=member_subscriptions,
                        first_of_month=target_month,
                        rhythm=rhythm,
                        cache=cache,
                        generated_payments=generated_payments,
                        in_trial=in_trial,
                    )
                )
            except MissingPickupLocationError as error:
                # Isolate the fault to this member: a single member with an
                # incomplete pickup-location history must not abort the whole
                # payment run (this builder runs for every member at once, both
                # in the daily cron and the future-payments view).
                logger.error(
                    "Skipping delivery charges for member %s: %s", member.id, error
                )

        return payments_to_create

    @classmethod
    def build_payments_for_member(
        cls,
        member: Member,
        contracts: set[Subscription],
        first_of_month: datetime.date,
        rhythm,
        cache: dict,
        generated_payments: set[Payment],
        in_trial: bool,
    ) -> list[Payment]:
        first_day_of_rhythm_period = (
            MemberPaymentRhythmService.get_first_day_of_rhythm_period(
                rhythm=rhythm, reference_date=first_of_month, cache=cache
            )
        )
        last_day_of_rhythm_period = (
            MemberPaymentRhythmService.get_last_day_of_rhythm_period(
                rhythm=rhythm, reference_date=first_of_month, cache=cache
            )
        )
        payment_start_date = get_parameter_value(
            key=ParameterKeys.PAYMENT_START_DATE, cache=cache
        )
        first_day_of_rhythm_period = max(payment_start_date, first_day_of_rhythm_period)
        if first_day_of_rhythm_period > last_day_of_rhythm_period:
            return []

        delivery_dates = cls.get_billable_delivery_dates_in_range(
            subscriptions=contracts,
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            cache=cache,
        )
        delivery_dates_by_pickup_location = (
            cls._group_delivery_dates_by_pickup_location(
                member_id=member.id, delivery_dates=delivery_dates, cache=cache
            )
        )

        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )
        due_date = MonthPaymentBuilderUtils.get_payment_due_date(
            first_of_month=first_of_month,
            in_trial=in_trial,
            contracts=contracts,
            cache=cache,
        )

        # Past delivery-charge payments for this member and period, grouped by the
        # pickup location they belong to. The per-location grouping is what makes
        # the already_paid idempotency location-scoped: two locations can have
        # overlapping date ranges (a member returning to a former location), so a
        # range-only lookup would let them contaminate each other.
        past_payments_by_pickup_location = cls._group_past_payments_by_pickup_location(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            cache=cache,
            generated_payments=generated_payments,
        )

        # A location that no longer has any billable delivery this period but was
        # billed before still needs a group so its charge can be refunded.
        pickup_location_ids = set(delivery_dates_by_pickup_location) | set(
            past_payments_by_pickup_location
        )

        payments = []
        for pickup_location_id in sorted(
            pickup_location_ids,
            key=lambda location_id: cls._sort_key_for_pickup_location(
                location_id,
                delivery_dates_by_pickup_location,
                past_payments_by_pickup_location,
            ),
        ):
            location_dates = delivery_dates_by_pickup_location.get(
                pickup_location_id, set()
            )
            past_payments = past_payments_by_pickup_location.get(pickup_location_id, [])

            total_to_pay = sum(
                (
                    PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
                        pickup_location_id=pickup_location_id,
                        reference_date=delivery_date,
                        cache=cache,
                    )
                    for delivery_date in location_dates
                ),
                start=Decimal(0),
            )
            already_paid = sum(
                (payment.amount for payment in past_payments), start=Decimal(0)
            )
            amount = (total_to_pay - already_paid).quantize(Decimal("0.01"))
            if amount == 0:
                continue

            if location_dates:
                range_start = min(location_dates)
                range_end = max(location_dates)
            else:
                range_start = min(
                    payment.subscription_payment_range_start
                    for payment in past_payments
                )
                range_end = max(
                    payment.subscription_payment_range_end for payment in past_payments
                )

            payments.append(
                Payment(
                    due_date=due_date,
                    amount=amount,
                    mandate_ref=mandate_ref,
                    status=Payment.PaymentStatus.DUE,
                    type=cls.PAYMENT_TYPE_DELIVERY_CHARGE,
                    subscription_payment_range_start=range_start,
                    subscription_payment_range_end=range_end,
                    pickup_location_id=pickup_location_id,
                )
            )

        return payments

    @classmethod
    def _sort_key_for_pickup_location(
        cls,
        pickup_location_id: str,
        delivery_dates_by_pickup_location: dict[str, set[datetime.date]],
        past_payments_by_pickup_location: dict[str, list[Payment]],
    ) -> datetime.date:
        location_dates = delivery_dates_by_pickup_location.get(pickup_location_id)
        if location_dates:
            return min(location_dates)
        return min(
            payment.subscription_payment_range_start
            for payment in past_payments_by_pickup_location[pickup_location_id]
        )

    @classmethod
    def _group_past_payments_by_pickup_location(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        mandate_ref,
        cache: dict,
        generated_payments: set[Payment],
    ) -> dict[str, list[Payment]]:
        past_payments = MonthPaymentBuilderUtils.get_relevant_past_payments(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            payment_type=cls.PAYMENT_TYPE_DELIVERY_CHARGE,
            cache=cache,
            generated_payments=generated_payments,
        )
        past_payments_by_pickup_location: dict[str, list[Payment]] = {}
        for payment in past_payments:
            past_payments_by_pickup_location.setdefault(
                payment.pickup_location_id, []
            ).append(payment)
        return past_payments_by_pickup_location

    @classmethod
    def _group_subscriptions_by_member(
        cls, subscriptions
    ) -> dict[Member, set[Subscription]]:
        subscriptions_by_member: dict[Member, set[Subscription]] = {}
        for subscription in subscriptions:
            subscriptions_by_member.setdefault(subscription.member, set()).add(
                subscription
            )
        return subscriptions_by_member

    @classmethod
    def _group_delivery_dates_by_pickup_location(
        cls,
        member_id: str,
        delivery_dates: set[datetime.date],
        cache: dict,
    ) -> dict[str, set[datetime.date]]:
        delivery_dates_by_pickup_location: dict[str, set[datetime.date]] = {}
        for delivery_date in delivery_dates:
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=member_id, reference_date=delivery_date, cache=cache
                )
            )
            if pickup_location_id is None:
                raise MissingPickupLocationError(
                    f"Member {member_id} has a billable delivery on {delivery_date} "
                    f"but no pickup location assigned on that date."
                )
            delivery_dates_by_pickup_location.setdefault(pickup_location_id, set()).add(
                delivery_date
            )
        return delivery_dates_by_pickup_location

    @classmethod
    def get_billable_delivery_dates_in_range(
        cls,
        subscriptions,
        range_start: datetime.date,
        range_end: datetime.date,
        cache: dict,
    ) -> set[datetime.date]:
        member = get_any_element_from_set(subscriptions).member

        candidate_dates: set[datetime.date] = set()
        for subscription in subscriptions:
            window_start = max(range_start, subscription.start_date)
            window_end = min(range_end, subscription.end_date)
            if window_start > window_end:
                continue
            candidate_dates.update(
                cls._get_delivery_dates_within_range(
                    subscription=subscription,
                    window_start=window_start,
                    window_end=window_end,
                    cache=cache,
                )
            )

        # A joker replaces a delivery with a paid week off, so no delivery reaches
        # the pickup location and no charge applies. A donation still produces a
        # delivery (it is redistributed), so the charge does apply - donation weeks
        # are intentionally not filtered out here.
        result: set[datetime.date] = set()
        for delivery_date in candidate_dates:
            if JokerManagementService.does_member_have_a_joker_in_week(
                member=member, reference_date=delivery_date, cache=cache
            ):
                continue
            result.add(delivery_date)
        return result

    @classmethod
    def _get_delivery_dates_within_range(
        cls,
        subscription: Subscription,
        window_start: datetime.date,
        window_end: datetime.date,
        cache: dict,
    ) -> list[datetime.date]:
        result: list[datetime.date] = []
        current_date = window_start - datetime.timedelta(days=1)
        while current_date <= window_end:
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=subscription.member_id,
                    reference_date=max(current_date, window_start),
                    cache=cache,
                )
            )
            if pickup_location_id is None:
                raise MissingPickupLocationError(
                    f"Member {subscription.member_id} has subscription {subscription.id} "
                    f"with a delivery scheduled around {current_date} but no pickup "
                    f"location assigned on that date."
                )
            next_date = DeliveryDateCalculator.get_next_delivery_date_for_product_type(
                reference_date=current_date,
                pickup_location_id=pickup_location_id,
                product_type=subscription.product.type,
                check_for_weeks_without_delivery=True,
                cache=cache,
            )
            if next_date is None or next_date > window_end:
                return result
            if next_date >= window_start:
                result.append(next_date)
            current_date = next_date
        return result
