import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.payments.models import MemberPaymentRhythm
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
from tapir.wirgarten.models import Member, Payment, Subscription


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

        subscriptions_by_member = cls.group_subscriptions_by_member(subscriptions)

        payments_to_create = []
        for member, member_subscriptions in subscriptions_by_member.items():
            if in_trial:
                rhythm = MemberPaymentRhythm.Rhythm.MONTHLY.value
            else:
                rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                    member=member, reference_date=target_month, cache=cache
                )

            payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
                member=member,
                first_of_month=target_month,
                contracts=member_subscriptions,
                rhythm=rhythm,
                cache=cache,
                generated_payments=generated_payments,
                in_trial=in_trial,
                payment_type=cls.PAYMENT_TYPE_DELIVERY_CHARGE,
                total_to_pay_function=cls.get_total_to_pay,
                allow_negative_amounts=True,
            )
            if payment is not None:
                payments_to_create.append(payment)

        return payments_to_create

    @classmethod
    def group_subscriptions_by_member(
        cls, subscriptions
    ) -> dict[Member, set[Subscription]]:
        subscriptions_by_member: dict[Member, set[Subscription]] = {}
        for subscription in subscriptions:
            subscriptions_by_member.setdefault(subscription.member, set()).add(
                subscription
            )
        return subscriptions_by_member

    @classmethod
    def get_total_to_pay(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        contracts,
        cache: dict,
    ) -> Decimal:
        if not contracts:
            return Decimal(0)

        member_id = next(iter(contracts)).member_id
        delivery_dates = cls.get_billable_delivery_dates_in_range(
            subscriptions=contracts,
            range_start=range_start,
            range_end=range_end,
            cache=cache,
        )

        total = Decimal(0)
        for delivery_date in delivery_dates:
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=member_id,
                    reference_date=delivery_date,
                    cache=cache,
                )
            )
            total += PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
                pickup_location_id=pickup_location_id,
                reference_date=delivery_date,
                cache=cache,
            )
        return total

    @classmethod
    def get_billable_delivery_dates_in_range(
        cls,
        subscriptions,
        range_start: datetime.date,
        range_end: datetime.date,
        cache: dict,
    ) -> set[datetime.date]:
        candidates_by_member: dict[str, tuple] = {}
        for subscription in subscriptions:
            window_start = max(range_start, subscription.start_date)
            window_end = min(range_end, subscription.end_date)
            if window_start > window_end:
                continue
            for delivery_date in cls._iter_delivery_dates_for_subscription(
                subscription=subscription,
                window_start=window_start,
                window_end=window_end,
                cache=cache,
            ):
                member_id = subscription.member_id
                existing = candidates_by_member.get(member_id)
                if existing is None:
                    candidates_by_member[member_id] = (subscription.member, set())
                candidates_by_member[member_id][1].add(delivery_date)

        result: set[datetime.date] = set()
        for member, delivery_dates in candidates_by_member.values():
            for delivery_date in delivery_dates:
                if JokerManagementService.does_member_have_a_joker_in_week(
                    member=member, reference_date=delivery_date, cache=cache
                ):
                    continue
                if DeliveryDonationManager.does_member_have_a_donation_in_week(
                    member=member, reference_date=delivery_date, cache=cache
                ):
                    continue
                result.add(delivery_date)
        return result

    @classmethod
    def _iter_delivery_dates_for_subscription(
        cls,
        subscription: Subscription,
        window_start: datetime.date,
        window_end: datetime.date,
        cache: dict,
    ):
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
                return
            next_date = DeliveryDateCalculator.get_next_delivery_date_for_product_type(
                reference_date=current_date,
                pickup_location_id=pickup_location_id,
                product_type=subscription.product.type,
                check_for_weeks_without_delivery=True,
                cache=cache,
            )
            if next_date is None or next_date > window_end:
                return
            if next_date >= window_start:
                yield next_date
            current_date = next_date
