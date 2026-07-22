import datetime
from decimal import Decimal

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.payments.models import MemberCredit
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


class MonthPaymentBuilderDeliveryCharges:
    PAYMENT_TYPE_DELIVERY_CHARGE = "payment_type_delivery_charge"

    @classmethod
    def build_payments_for_delivery_charges(
        cls,
        current_month: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
        generated_credits: set[MemberCredit],
    ) -> tuple[list[Payment], list[MemberCredit]]:
        # Delivery charges are billed in a single pass over all of a member's
        # subscriptions at the member's real rhythm, deliberately NOT split into
        # trial/non-trial passes like subscription payments are. The charge is one
        # amount per delivery date per pickup location, and the already_paid
        # idempotency is scoped by mandate + pickup location. A trial/non-trial
        # split would bill the same dates in two differently-sized windows against
        # that one scope, which makes the daily rerun oscillate between spurious
        # refunds and counter-charges. A trial cancellation is refunded by the
        # normal credit mechanism (fewer delivery dates next run).
        subscriptions = MonthPaymentBuilderSubscriptions.get_current_and_renewed_subscriptions_ignoring_trial_state(
            cache=cache, first_of_month=current_month
        )
        subscriptions_by_member = cls._group_subscriptions_by_member(subscriptions)

        payments_to_create: list[Payment] = []
        credits_to_create: list[MemberCredit] = []
        for member, member_subscriptions in subscriptions_by_member.items():
            rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member, reference_date=current_month, cache=cache
            )
            member_payments, member_credits = cls.build_payments_for_member(
                member=member,
                contracts=member_subscriptions,
                first_of_month=current_month,
                rhythm=rhythm,
                cache=cache,
                generated_payments=generated_payments,
                generated_credits=generated_credits,
            )
            payments_to_create.extend(member_payments)
            credits_to_create.extend(member_credits)

        return payments_to_create, credits_to_create

    @classmethod
    def build_payments_for_member(
        cls,
        member: Member,
        contracts: set[Subscription],
        first_of_month: datetime.date,
        rhythm,
        cache: dict,
        generated_payments: set[Payment],
        generated_credits: set[MemberCredit],
    ) -> tuple[list[Payment], list[MemberCredit]]:
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
            return [], []

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

        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )
        due_date = MonthPaymentBuilderUtils.get_payment_due_date(
            first_of_month=first_of_month,
            in_trial=False,
            contracts=contracts,
            cache=cache,
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
            generated_credits=generated_credits,
        )

        # A location that no longer has any billable delivery this period but was
        # billed before still needs a group so its charge can be refunded.
        pickup_location_ids = set(delivery_dates_by_pickup_location_id) | set(
            past_payments_by_pickup_location_id
        )

        payments: list[Payment] = []
        credits: list[MemberCredit] = []
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

            if amount > 0:
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
            else:
                pickup_location_name = TapirCache.get_pickup_location_by_id(
                    cache=cache, pickup_location_id=pickup_location_id
                ).name
                credits.append(
                    MemberCredit(
                        due_date=range_start,
                        member=member,
                        amount=-amount,
                        purpose=MemberCredit.PLACEHOLDER_PURPOSE,
                        comment=f"Gutschrift Lieferzuschlag, Abholort {pickup_location_name}",
                        source=cls.PAYMENT_TYPE_DELIVERY_CHARGE,
                        pickup_location_id=pickup_location_id,
                    )
                )

        return payments, credits

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
        generated_credits: set[MemberCredit],
    ) -> dict[str, list[MemberCredit]]:
        relevant_credits = MonthPaymentBuilderUtils.get_relevant_credits(
            range_start=range_start,
            range_end=range_end,
            member_id=member_id,
            payment_type=cls.PAYMENT_TYPE_DELIVERY_CHARGE,
            cache=cache,
            generated_credits=generated_credits,
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
