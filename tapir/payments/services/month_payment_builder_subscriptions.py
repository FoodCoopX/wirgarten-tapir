import datetime
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ImproperlyConfigured

from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.deliveries.services.subscription_price_type_decider import (
    SubscriptionPricingStrategyDecider,
)
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month, get_any_element_from_set
from tapir.wirgarten.constants import (
    NO_DELIVERY,
    WEEKLY,
    ODD_WEEKS,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
    CUSTOM_CYCLE,
)
from tapir.wirgarten.models import (
    Subscription,
    Payment,
    Member,
    ProductType,
)


class MonthPaymentBuilderSubscriptions:
    @classmethod
    def build_payments_for_subscriptions(
        cls,
        current_month: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
        in_trial: bool,
    ) -> list[Payment]:
        target_month = current_month
        if in_trial:
            target_month = (current_month - relativedelta(months=1)).replace(day=1)

        current_and_renewed_subscriptions = cls.get_current_and_renewed_subscriptions(
            cache=cache, first_of_month=target_month, is_in_trial=in_trial
        )

        subscriptions_by_member_and_product_type = (
            cls.group_subscriptions_by_member_and_product_type(
                current_and_renewed_subscriptions
            )
        )

        payments_to_create = []

        for (
            member,
            subscriptions_by_product_type,
        ) in subscriptions_by_member_and_product_type.items():
            for product_type, subscriptions in subscriptions_by_product_type.items():
                rhythm = cls.get_payment_rhythm(
                    subscriptions, current_month, in_trial, member, cache
                )

                payment = (
                    MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
                        member=member,
                        first_of_month=target_month,
                        contracts=subscriptions,
                        payment_type=product_type.name,
                        rhythm=rhythm,
                        cache=cache,
                        generated_payments=generated_payments,
                        in_trial=in_trial,
                        total_to_pay_function=cls.get_total_to_pay,
                        allow_negative_amounts=False,
                    )
                )
                if payment is not None:
                    payments_to_create.append(payment)

        return payments_to_create

    @classmethod
    def get_payment_rhythm(
        cls,
        subscriptions: set[Subscription],
        current_month: date,
        in_trial: bool,
        member: Member,
        cache: dict,
    ) -> str:
        if cls.force_monthly_payment_rhythm(
            in_trial=in_trial, subscriptions=subscriptions
        ):
            return MemberPaymentRhythm.Rhythm.MONTHLY

        return MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member, reference_date=current_month, cache=cache
        )

    @classmethod
    def force_monthly_payment_rhythm(
        cls, in_trial: bool, subscriptions: set[Subscription]
    ):
        if in_trial:
            return True

        if len(subscriptions) == 0:
            return False

        return (
            get_any_element_from_set(subscriptions).product.type.delivery_cycle
            == CUSTOM_CYCLE[0]
        )

    @classmethod
    def get_total_to_pay(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        contracts: list[Subscription],
        cache: dict,
    ) -> Decimal:
        subscriptions_active_within_period = [
            subscription
            for subscription in contracts
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=range_start,
                range_1_end=range_end,
                range_2_start=subscription.start_date,
                range_2_end=subscription.end_date,
            )
        ]
        total_to_pay = sum(
            [
                cls.get_amount_to_pay_for_subscription_within_range(
                    subscription=subscription,
                    range_start=range_start,
                    range_end=range_end,
                    cache=cache,
                )
                for subscription in subscriptions_active_within_period
            ],
            Decimal(0),
        )
        return total_to_pay

    @classmethod
    def get_amount_to_pay_for_subscription_within_range(
        cls,
        subscription: Subscription,
        range_start: datetime.date,
        range_end: datetime.date,
        cache: dict,
    ) -> Decimal:
        number_of_full_month_to_pay, number_of_single_deliveries_to_pay = (
            cls.get_number_of_months_and_deliveries_to_pay(
                range_start=range_start,
                range_end=range_end,
                subscription=subscription,
                cache=cache,
            )
        )

        monthly_price = SubscriptionPriceCalculator.get_monthly_price(
            subscription=subscription, reference_date=range_start, cache=cache
        )
        full_months_price = monthly_price * number_of_full_month_to_pay

        single_deliveries_price = (
            number_of_single_deliveries_to_pay
            * DeliveryPriceCalculator.get_price_of_single_delivery_for_subscription(
                subscription=subscription, at_date=range_start, cache=cache
            )
        )

        return full_months_price + single_deliveries_price

    @classmethod
    def get_number_of_months_and_deliveries_to_pay(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        subscription: Subscription,
        cache: dict,
    ):
        current_month = range_start
        number_of_full_month_to_pay = 0
        number_of_single_deliveries_to_pay = 0
        force_price_per_delivery = (
            SubscriptionPricingStrategyDecider.is_price_by_delivery(
                subscription.product.type.delivery_cycle
            )
        )

        while current_month < range_end:
            if not DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=range_start,
                range_1_end=range_end,
                range_2_start=subscription.start_date,
                range_2_end=subscription.end_date,
            ):
                continue

            if (
                cls.is_month_fully_covered_by_subscription(
                    subscription=subscription, first_of_month=current_month
                )
                and not force_price_per_delivery
            ):
                number_of_full_month_to_pay += 1
            else:
                number_of_deliveries = cls.get_number_of_deliveries_in_month(
                    subscription=subscription, first_of_month=current_month, cache=cache
                )
                if (
                    cls.should_pay_full_month_price(
                        number_of_deliveries=number_of_deliveries,
                        delivery_cycle=subscription.product.type.delivery_cycle,
                    )
                    and not force_price_per_delivery
                ):
                    number_of_full_month_to_pay += 1
                else:
                    number_of_single_deliveries_to_pay += number_of_deliveries

            current_month += MemberPaymentRhythmService.RELATIVE_DELTA_ONE_MONTH
        return number_of_full_month_to_pay, number_of_single_deliveries_to_pay

    @classmethod
    def is_month_fully_covered_by_subscription(
        cls,
        subscription: Subscription,
        first_of_month: datetime.date,
    ):
        if not DateRangeOverlapChecker.do_ranges_overlap(
            range_1_start=first_of_month,
            range_1_end=get_last_day_of_month(first_of_month),
            range_2_start=subscription.start_date,
            range_2_end=subscription.end_date,
        ):
            return False

        if (
            first_of_month == subscription.start_date.replace(day=1)
            and subscription.start_date.day != 1
        ):
            return False
        if (
            first_of_month == subscription.end_date.replace(day=1)
            and subscription.end_date.day
            != get_last_day_of_month(subscription.end_date).day
        ):
            return False
        return True

    @classmethod
    def should_pay_full_month_price(
        cls, number_of_deliveries: int, delivery_cycle: str
    ):
        return (
            number_of_deliveries
            >= cls.get_number_of_deliveries_for_full_month_price(delivery_cycle)
        )

    @classmethod
    def get_number_of_deliveries_in_month(
        cls,
        subscription: Subscription,
        first_of_month: datetime.date,
        cache: dict,
    ):
        last_of_month = get_last_day_of_month(first_of_month)
        number_of_deliveries = 0

        # we start one day back so that deliveries on the first day of the month are counted
        current_date = first_of_month - datetime.timedelta(days=1)

        while current_date <= last_of_month:
            current_date = DeliveryDateCalculator.get_next_delivery_date_for_product_type(
                reference_date=current_date,
                pickup_location_id=MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=subscription.member_id,
                    reference_date=current_date,
                    cache=cache,
                ),
                product_type=subscription.product.type,
                check_for_weeks_without_delivery=False,
                cache=cache,
            )
            if current_date is None:
                break
            if (
                current_date <= last_of_month
                and subscription.start_date <= current_date <= subscription.end_date
            ):
                number_of_deliveries += 1

        return number_of_deliveries

    @classmethod
    def group_subscriptions_by_member_and_product_type(
        cls, subscriptions: list[Subscription]
    ) -> dict[Member, dict[ProductType, set[Subscription]]]:
        subscriptions_by_member_and_product_type: dict[
            Member, dict[ProductType, set[Subscription]]
        ] = {}
        for subscription in subscriptions:
            if subscription.member not in subscriptions_by_member_and_product_type:
                subscriptions_by_member_and_product_type[subscription.member] = {}

            subscriptions_by_product_type = subscriptions_by_member_and_product_type[
                subscription.member
            ]
            if subscription.product.type not in subscriptions_by_product_type:
                subscriptions_by_product_type[subscription.product.type] = set()

            subscriptions_by_product_type[subscription.product.type].add(subscription)

        return subscriptions_by_member_and_product_type

    @classmethod
    def get_current_and_renewed_subscriptions(
        cls, cache: dict, first_of_month: datetime.date, is_in_trial: bool
    ) -> list[Subscription]:
        existing_subscriptions = TapirCache.get_all_subscriptions(cache=cache)

        planned_renewed_subscriptions = [
            AutomaticSubscriptionRenewalService.build_renewed_subscription(
                subscription=subscription, cache=cache
            )
            for subscription in AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=first_of_month, cache=cache
            )
        ]
        subscriptions_in_trial = [
            subscription
            for subscription in existing_subscriptions.union(
                planned_renewed_subscriptions
            )
            if TrialPeriodManager.is_contract_in_trial(
                contract=subscription, reference_date=first_of_month, cache=cache
            )
            == is_in_trial
        ]
        return subscriptions_in_trial

    @classmethod
    def get_number_of_deliveries_for_full_month_price(cls, delivery_cycle: str):
        if delivery_cycle == NO_DELIVERY[0]:
            return 0
        if delivery_cycle == WEEKLY[0]:
            return 4
        if delivery_cycle in {EVEN_WEEKS[0], ODD_WEEKS[0]}:
            return 2
        if delivery_cycle in {EVERY_FOUR_WEEKS[0], CUSTOM_CYCLE[0]}:
            return 1
        raise ImproperlyConfigured("Unknown delivery cycle: " + delivery_cycle)
