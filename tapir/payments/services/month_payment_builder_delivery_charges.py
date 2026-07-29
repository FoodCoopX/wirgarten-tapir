import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.payments.models import MemberCredit, MemberPaymentRhythm
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
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import Member, Payment, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys


class MissingPickupLocationError(ValueError):
    """
    Raised when a member has a billable delivery on a date but no pickup
    location assigned on that date - an invalid state we cannot bill for.
    """


class LocationDelta:
    def __init__(
        self,
        pickup_location_id: str,
        amount: Decimal,
        range_start: datetime.date,
        range_end: datetime.date,
    ):
        self.pickup_location_id = pickup_location_id
        self.amount = amount
        self.range_start = range_start
        self.range_end = range_end


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
        # Like the subscription and solidarity builders, delivery charges are
        # billed in two passes so that contracts still in their trial period are
        # only billed in arrears (never prepaid): the in-trial pass bills the
        # previous month at a forced monthly rhythm, the non-trial pass bills the
        # current month forward at the member's real rhythm. Refunds (a member
        # switching away from a pickup location they prepaid) are not created
        # here - they are created synchronously when the location changes, see
        # build_refund_credits_for_pickup_location_change.
        target_month = current_month
        if in_trial:
            target_month = (target_month - relativedelta(months=1)).replace(day=1)

        subscriptions = (
            MonthPaymentBuilderSubscriptions.get_current_and_renewed_subscriptions(
                cache=cache, first_of_month=target_month, is_in_trial=in_trial
            )
        )
        subscriptions_by_member = cls._group_subscriptions_by_member(subscriptions)

        payments_to_create: list[Payment] = []
        for member, member_subscriptions in subscriptions_by_member.items():
            if in_trial:
                rhythm = MemberPaymentRhythm.Rhythm.MONTHLY.value
            else:
                rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                    member=member, reference_date=target_month, cache=cache
                )
            payments_to_create.extend(
                cls.build_payments_for_member(
                    member=member,
                    contracts=member_subscriptions,
                    first_of_month=target_month,
                    rhythm=rhythm,
                    in_trial=in_trial,
                    cache=cache,
                    generated_payments=generated_payments,
                )
            )

        return payments_to_create

    @classmethod
    def build_payments_for_member(
        cls,
        member: Member,
        contracts: set[Subscription],
        first_of_month: datetime.date,
        rhythm,
        in_trial: bool,
        cache: dict,
        generated_payments: set[Payment],
    ) -> list[Payment]:
        rhythm_period = cls._get_rhythm_period(
            rhythm=rhythm, first_of_month=first_of_month, cache=cache
        )
        if rhythm_period is None:
            return []
        first_day_of_rhythm_period, last_day_of_rhythm_period = rhythm_period

        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )
        due_date = MonthPaymentBuilderUtils.get_payment_due_date(
            first_of_month=first_of_month,
            in_trial=in_trial,
            contracts=contracts,
            cache=cache,
        )

        payments: list[Payment] = []
        for delta in cls._get_location_deltas(
            member=member,
            contracts=contracts,
            first_day_of_rhythm_period=first_day_of_rhythm_period,
            last_day_of_rhythm_period=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            cache=cache,
            generated_payments=generated_payments,
        ):
            # Never bill a negative amount: an over-payment (e.g. a shorter trial
            # window seeing a longer prepaid payment) is left untouched here, the
            # same way the subscription builder clamps at zero. Genuine refunds
            # are created at pickup-location switch time instead.
            if delta.amount <= 0:
                continue
            payments.append(
                Payment(
                    due_date=due_date,
                    amount=delta.amount,
                    mandate_ref=mandate_ref,
                    status=Payment.PaymentStatus.DUE,
                    type=cls.PAYMENT_TYPE_DELIVERY_CHARGE,
                    subscription_payment_range_start=delta.range_start,
                    subscription_payment_range_end=delta.range_end,
                    pickup_location_id=delta.pickup_location_id,
                )
            )

        return payments

    @classmethod
    def build_refund_credits_for_pickup_location_change(
        cls,
        member: Member,
        reference_date: datetime.date,
        cache: dict,
    ) -> list[MemberCredit]:
        # A member who prepaid a pickup location's delivery charge and then moves
        # away from it mid-period is refunded the prepaid-but-no-longer-owed part
        # as a MemberCredit for that location. Because it runs once, at the moment
        # the location changes (not on every daily payment rerun), it cannot
        # oscillate. The credit is netted back against the member's delivery
        # charges by the payment builder via its pickup-location-scoped
        # already_paid computation.
        first_of_month = reference_date.replace(day=1)
        subscriptions = MonthPaymentBuilderSubscriptions.get_current_and_renewed_subscriptions_ignoring_trial_state(
            cache=cache, first_of_month=first_of_month
        )
        contracts = {
            subscription
            for subscription in subscriptions
            if subscription.member_id == member.id
        }
        if len(contracts) == 0:
            return []

        rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member, reference_date=first_of_month, cache=cache
        )
        rhythm_period = cls._get_rhythm_period(
            rhythm=rhythm, first_of_month=first_of_month, cache=cache
        )
        if rhythm_period is None:
            return []
        first_day_of_rhythm_period, last_day_of_rhythm_period = rhythm_period

        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )

        credits: list[MemberCredit] = []
        for delta in cls._get_location_deltas(
            member=member,
            contracts=contracts,
            first_day_of_rhythm_period=first_day_of_rhythm_period,
            last_day_of_rhythm_period=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            cache=cache,
            generated_payments=set(),
        ):
            if delta.amount >= 0:
                continue
            pickup_location_name = TapirCache.get_pickup_location_by_id(
                cache=cache, pickup_location_id=delta.pickup_location_id
            ).name
            credits.append(
                MemberCredit(
                    due_date=delta.range_start,
                    member=member,
                    amount=-delta.amount,
                    purpose=MemberCredit.PLACEHOLDER_PURPOSE,
                    comment=f"Gutschrift Lieferzuschlag, Abholort {pickup_location_name}",
                    source=cls.PAYMENT_TYPE_DELIVERY_CHARGE,
                    pickup_location_id=delta.pickup_location_id,
                )
            )

        return credits

    @classmethod
    def _get_rhythm_period(
        cls, rhythm, first_of_month: datetime.date, cache: dict
    ) -> tuple[datetime.date, datetime.date] | None:
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
            return None
        return first_day_of_rhythm_period, last_day_of_rhythm_period

    @classmethod
    def _get_location_deltas(
        cls,
        member: Member,
        contracts: set[Subscription],
        first_day_of_rhythm_period: datetime.date,
        last_day_of_rhythm_period: datetime.date,
        mandate_ref,
        cache: dict,
        generated_payments: set[Payment],
    ) -> list[LocationDelta]:
        # The single source of truth for "what does each pickup location owe or
        # over-pay this member for this period": the payment path keeps the
        # positive deltas, the refund path keeps the negative ones.
        delivery_dates = cls.get_billable_delivery_dates_in_range(
            subscriptions=contracts,
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            cache=cache,
        )
        delivery_dates_by_pickup_location_id = (
            cls._group_delivery_dates_by_pickup_location_id(
                member_id=member.id, delivery_dates=delivery_dates, cache=cache
            )
        )

        # Past delivery-charge payments and credits for this member and period,
        # grouped by the pickup location they belong to. The per-location grouping
        # is what makes the already_paid idempotency location-scoped: two locations
        # can have overlapping date ranges (a member returning to a former
        # location), so a range-only lookup would let them contaminate each other.
        past_payments_by_pickup_location_id = (
            cls._group_past_payments_by_pickup_location_id(
                range_start=first_day_of_rhythm_period,
                range_end=last_day_of_rhythm_period,
                mandate_ref=mandate_ref,
                cache=cache,
                generated_payments=generated_payments,
            )
        )
        credits_by_pickup_location_id = cls._group_credits_by_pickup_location_id(
            member_id=member.id,
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            cache=cache,
        )

        # A location that no longer has any billable delivery this period but was
        # billed before still needs a delta so its charge can be refunded.
        pickup_location_ids = set(delivery_dates_by_pickup_location_id) | set(
            past_payments_by_pickup_location_id
        )
        # A delivery-charge payment with no pickup location is an anomaly we
        # cannot attribute to a location, so it takes part in neither a charge
        # nor a refund (and there is no location to name for a credit).
        pickup_location_ids.discard(None)

        deltas: list[LocationDelta] = []
        for pickup_location_id in pickup_location_ids:
            location_dates = delivery_dates_by_pickup_location_id.get(
                pickup_location_id, set()
            )
            past_payments = past_payments_by_pickup_location_id.get(
                pickup_location_id, []
            )
            location_credits = credits_by_pickup_location_id.get(pickup_location_id, [])

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
            ) - sum((credit.amount for credit in location_credits), start=Decimal(0))
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

            deltas.append(
                LocationDelta(
                    pickup_location_id=pickup_location_id,
                    amount=amount,
                    range_start=range_start,
                    range_end=range_end,
                )
            )

        return deltas

    @classmethod
    def _group_past_payments_by_pickup_location_id(
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
        past_payments_by_pickup_location_id: dict[str, list[Payment]] = {}
        for payment in past_payments:
            past_payments_by_pickup_location_id.setdefault(
                payment.pickup_location_id, []
            ).append(payment)
        return past_payments_by_pickup_location_id

    @classmethod
    def _group_credits_by_pickup_location_id(
        cls,
        member_id: str,
        range_start: datetime.date,
        range_end: datetime.date,
        cache: dict,
    ) -> dict[str, list[MemberCredit]]:
        relevant_credits = MonthPaymentBuilderUtils.get_relevant_credits(
            range_start=range_start,
            range_end=range_end,
            member_id=member_id,
            payment_type=cls.PAYMENT_TYPE_DELIVERY_CHARGE,
            cache=cache,
            generated_credits=set(),
        )
        credits_by_pickup_location_id: dict[str, list[MemberCredit]] = {}
        for credit in relevant_credits:
            credits_by_pickup_location_id.setdefault(
                credit.pickup_location_id, []
            ).append(credit)
        return credits_by_pickup_location_id

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
    def _group_delivery_dates_by_pickup_location_id(
        cls,
        member_id: str,
        delivery_dates: set[datetime.date],
        cache: dict,
    ) -> dict[str, set[datetime.date]]:
        # Every delivery date here already passed through
        # _get_delivery_dates_within_range, which raises if the member has no
        # pickup location on that date, so the lookup below is never None.
        delivery_dates_by_pickup_location_id: dict[str, set[datetime.date]] = {}
        for delivery_date in delivery_dates:
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=member_id, reference_date=delivery_date, cache=cache
                )
            )
            delivery_dates_by_pickup_location_id.setdefault(
                pickup_location_id, set()
            ).add(delivery_date)
        return delivery_dates_by_pickup_location_id

    @classmethod
    def get_billable_delivery_dates_in_range(
        cls,
        subscriptions,
        range_start: datetime.date,
        range_end: datetime.date,
        cache: dict,
    ) -> set[datetime.date]:
        # Joker and donation weeks are both billed: the box is still produced and
        # reaches the pickup location, so the charge applies. The joker's value
        # (including this charge) is credited to the member separately, via the
        # "Joker Gutschriftwert" export column, not by skipping the charge here.
        delivery_dates: set[datetime.date] = set()
        for subscription in subscriptions:
            if subscription.product.type.delivery_cycle == NO_DELIVERY[0]:
                continue
            window_start = max(range_start, subscription.start_date)
            window_end = min(range_end, subscription.end_date)
            if window_start > window_end:
                continue
            delivery_dates.update(
                cls._get_delivery_dates_within_range(
                    subscription=subscription,
                    window_start=window_start,
                    window_end=window_end,
                    cache=cache,
                )
            )
        return delivery_dates

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
            result.append(next_date)
            current_date = next_date
        return result
