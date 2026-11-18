import datetime
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils.formats import date_format

from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.deliveries.services.monthly_delivery_date_counter import (
    MonthlyDeliveryDateCounter,
)
from tapir.deliveries.services.partial_month_calculation_mode_decider import (
    PartialMonthCalculationModeDecider,
)
from tapir.deliveries.services.subscription_price_type_decider import (
    SubscriptionPricingStrategyDecider,
)
from tapir.utils.dataclasses import CalculationPart
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.subscriptions.services.subscription_calculation_name_builder import (
    SubscriptionCalculationNameBuilder,
)
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month, get_any_element
from tapir.wirgarten.constants import (
    NO_DELIVERY,
    WEEKLY,
    ODD_WEEKS,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
    CUSTOM_CYCLE,
)
from tapir.wirgarten.utils import format_currency
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
        member_id: str | None = None,
    ) -> list[Payment]:
        target_month = current_month
        if in_trial:
            target_month = (current_month - relativedelta(months=1)).replace(day=1)

        current_and_renewed_subscriptions = cls.get_current_and_renewed_subscriptions(
            cache=cache,
            first_of_month=target_month,
            is_in_trial=in_trial,
            member_id=member_id,
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
                        calculation_parts_function=cls.get_calculation_parts,
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
            get_any_element(subscriptions).product.type.delivery_cycle
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
        return sum(
            (
                part.value
                for part in cls.get_calculation_parts(
                    range_start=range_start,
                    range_end=range_end,
                    contracts=contracts,
                    cache=cache,
                )
            ),
            Decimal(0),
        )

    @classmethod
    def get_calculation_parts(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        contracts: list[Subscription],
        cache: dict,
    ) -> list[CalculationPart]:
        subscriptions_active_within_period = sorted(
            (
                subscription
                for subscription in contracts
                if DateRangeOverlapChecker.do_ranges_overlap(
                    range_1_start=range_start,
                    range_1_end=range_end,
                    range_2_start=subscription.start_date,
                    range_2_end=subscription.end_date,
                )
            ),
            key=lambda subscription: (
                subscription.start_date,
                subscription.product.name,
            ),
        )
        return [
            part
            for subscription in subscriptions_active_within_period
            for part in cls._get_calculation_parts_for_subscription_within_range(
                subscription=subscription,
                range_start=range_start,
                range_end=range_end,
                cache=cache,
            )
        ]

    @classmethod
    def _get_calculation_parts_for_subscription_within_range(
        cls,
        subscription: Subscription,
        range_start: datetime.date,
        range_end: datetime.date,
        cache: dict,
    ) -> list[CalculationPart]:
        monthly_price = SubscriptionPriceCalculator.get_monthly_price(
            subscription=subscription, reference_date=range_start, cache=cache
        )
        price_of_single_delivery = (
            DeliveryPriceCalculator.get_price_of_single_delivery_for_subscription(
                subscription=subscription, at_date=range_start, cache=cache
            )
        )

        parts = []
        current_month = range_start
        while current_month < range_end:
            part = cls._build_calculation_part_for_subscription_within_month(
                subscription=subscription,
                first_of_month=current_month,
                monthly_price=monthly_price,
                price_of_single_delivery=price_of_single_delivery,
                cache=cache,
            )
            if part is not None:
                parts.append(part)
            current_month += relativedelta(months=1)

        return parts

    @classmethod
    def _build_calculation_part_for_subscription_within_month(
        cls,
        subscription: Subscription,
        first_of_month: datetime.date,
        monthly_price: Decimal,
        price_of_single_delivery: Decimal,
        cache: dict,
    ) -> CalculationPart | None:
        if not DateRangeOverlapChecker.do_ranges_overlap(
            range_1_start=first_of_month,
            range_1_end=get_last_day_of_month(first_of_month),
            range_2_start=subscription.start_date,
            range_2_end=subscription.end_date,
        ):
            return None

        prefix = f"{date_format(first_of_month, "F Y")}, {SubscriptionCalculationNameBuilder.build_name(subscription=subscription)}"
        delivery_cycle = subscription.product.type.delivery_cycle

        if SubscriptionPricingStrategyDecider.is_price_by_delivery(delivery_cycle):
            return cls._build_price_per_delivery_part(
                prefix=prefix,
                number_of_deliveries=cls._count_delivery_dates_of_subscription_in_month(
                    subscription=subscription,
                    first_of_month=first_of_month,
                    cache=cache,
                ),
                price_of_single_delivery=price_of_single_delivery,
            )

        if cls.is_month_fully_covered_by_subscription(
            subscription=subscription, first_of_month=first_of_month
        ):
            return CalculationPart(
                explanation=f"{prefix}: {format_currency(monthly_price)} € monatlich (voller Monat)",
                value=monthly_price,
            )

        if PartialMonthCalculationModeDecider.is_proportional_mode_active(
            first_of_month=first_of_month, cache=cache
        ):
            if delivery_cycle == NO_DELIVERY[0]:
                return cls._build_days_covered_part(
                    prefix=prefix,
                    subscription=subscription,
                    first_of_month=first_of_month,
                    monthly_price=monthly_price,
                )
            return cls._build_delivery_dates_covered_part(
                prefix=prefix,
                subscription=subscription,
                first_of_month=first_of_month,
                monthly_price=monthly_price,
                cache=cache,
            )

        number_of_deliveries = cls._count_delivery_dates_of_subscription_in_month(
            subscription=subscription, first_of_month=first_of_month, cache=cache
        )
        if cls.should_pay_full_month_price(
            number_of_deliveries=number_of_deliveries, delivery_cycle=delivery_cycle
        ):
            threshold = cls.get_number_of_deliveries_for_full_month_price(
                delivery_cycle
            )
            return CalculationPart(
                explanation=f"{prefix}: {format_currency(monthly_price)} € monatlich ({cls._build_count_label(number_of_deliveries, "Lieferung", "Lieferungen")}, voller Monatspreis ab {threshold})",
                value=monthly_price,
            )
        return cls._build_price_per_delivery_part(
            prefix=prefix,
            number_of_deliveries=number_of_deliveries,
            price_of_single_delivery=price_of_single_delivery,
        )

    @classmethod
    def _build_price_per_delivery_part(
        cls,
        prefix: str,
        number_of_deliveries: int,
        price_of_single_delivery: Decimal,
    ) -> CalculationPart:
        value = number_of_deliveries * price_of_single_delivery
        return CalculationPart(
            explanation=f"{prefix}: {cls._build_count_label(number_of_deliveries, "Lieferung", "Lieferungen")} à {format_currency(price_of_single_delivery)} € = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def _build_days_covered_part(
        cls,
        prefix: str,
        subscription: Subscription,
        first_of_month: datetime.date,
        monthly_price: Decimal,
    ) -> CalculationPart:
        days_covered = MonthPaymentBuilderUtils.get_number_of_days_covered_in_month(
            first_of_month=first_of_month,
            contract_start=subscription.start_date,
            contract_end=subscription.end_date,
        )
        days_in_month = get_last_day_of_month(first_of_month).day
        value = monthly_price * days_covered / days_in_month
        return CalculationPart(
            explanation=f"{prefix}: {format_currency(monthly_price)} € × {days_covered} von {days_in_month} Tagen = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def _build_delivery_dates_covered_part(
        cls,
        prefix: str,
        subscription: Subscription,
        first_of_month: datetime.date,
        monthly_price: Decimal,
        cache: dict,
    ) -> CalculationPart:
        total_dates = MonthlyDeliveryDateCounter.count_delivery_dates_in_month(
            member_id=subscription.member_id,
            product_type=subscription.product.type,
            first_of_month=first_of_month,
            contract_start=None,
            contract_end=None,
            cache=cache,
        )
        if total_dates == 0:
            return CalculationPart(
                explanation=f"{prefix}: keine Liefertermine im Monat = {format_currency(0)} €",
                value=Decimal(0),
            )

        subscription_dates = cls._count_delivery_dates_of_subscription_in_month(
            subscription=subscription, first_of_month=first_of_month, cache=cache
        )
        value = monthly_price * subscription_dates / total_dates
        return CalculationPart(
            explanation=f"{prefix}: {format_currency(monthly_price)} € × {subscription_dates} ÷ {cls._build_count_label(total_dates, "Liefertermin", "Liefertermine")} = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def _count_delivery_dates_of_subscription_in_month(
        cls, subscription: Subscription, first_of_month: datetime.date, cache: dict
    ) -> int:
        return MonthlyDeliveryDateCounter.count_delivery_dates_in_month(
            member_id=subscription.member_id,
            product_type=subscription.product.type,
            first_of_month=first_of_month,
            contract_start=subscription.start_date,
            contract_end=subscription.end_date,
            cache=cache,
        )

    @staticmethod
    def _build_count_label(count: int, singular: str, plural: str) -> str:
        return f"{count} {singular if count == 1 else plural}"

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
    def get_current_and_renewed_subscriptions_ignoring_trial_state(
        cls, cache: dict, first_of_month: datetime.date, member_id: str | None = None
    ) -> set[Subscription]:
        if member_id is None:
            existing_subscriptions = TapirCache.get_all_subscriptions(cache=cache)
        else:
            existing_subscriptions = set(
                TapirCache.get_all_subscriptions_for_member(
                    member_id=member_id, cache=cache
                )
            )
        subscriptions_to_renew = MonthPaymentBuilderUtils.filter_contracts_by_member(
            contracts=list(
                AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                    reference_date=first_of_month, cache=cache
                )
            ),
            member_id=member_id,
        )
        planned_renewed_subscriptions = {
            AutomaticSubscriptionRenewalService.build_renewed_subscription(
                subscription=subscription, cache=cache
            )
            for subscription in subscriptions_to_renew
        }
        return existing_subscriptions.union(planned_renewed_subscriptions)

    @classmethod
    def get_current_and_renewed_subscriptions(
        cls,
        cache: dict,
        first_of_month: datetime.date,
        is_in_trial: bool,
        member_id: str | None = None,
    ) -> list[Subscription]:
        return [
            subscription
            for subscription in cls.get_current_and_renewed_subscriptions_ignoring_trial_state(
                cache=cache, first_of_month=first_of_month, member_id=member_id
            )
            if TrialPeriodManager.is_contract_in_trial(
                contract=subscription, reference_date=first_of_month, cache=cache
            )
            == is_in_trial
        ]

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
        raise TapirImproperlyConfigured("Unknown delivery cycle: " + delivery_cycle)
