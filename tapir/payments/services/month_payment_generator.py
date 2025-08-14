import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.constants import (
    NO_DELIVERY,
    WEEKLY,
    ODD_WEEKS,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
)
from tapir.wirgarten.models import Subscription, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_or_create_mandate_ref


class MonthPaymentGenerator:
    @classmethod
    def generate_payments_for_month(cls, first_of_month: datetime.date, cache: dict):
        first_of_month = first_of_month.replace(day=1)

        payments_to_create_trial = cls.generate_payments_for_subscriptions_in_trial(
            reference_date=first_of_month, cache=cache
        )

        payments_to_create_no_trial = (
            cls.generate_payments_for_subscriptions_not_in_trial(
                first_of_month=first_of_month, cache=cache
            )
        )

        Payment.objects.bulk_create(
            payments_to_create_no_trial + payments_to_create_trial
        )

    @classmethod
    def generate_payments_for_subscriptions_not_in_trial(
        cls, first_of_month: datetime.date, cache: dict
    ):
        subscriptions = TapirCache.get_all_subscriptions(cache=cache)
        subscriptions = [
            subscription
            for subscription in subscriptions
            if not TrialPeriodManager.is_subscription_in_trial(
                subscription=subscription, reference_date=first_of_month, cache=cache
            )
        ]
        subscriptions_by_member_and_product_type = (
            cls.group_subscriptions_by_member_and_product_type(subscriptions)
        )

        payments_due_date = cls.get_payment_due_date_on_month(
            reference_date=first_of_month, cache=cache
        )
        payments_to_create = []

        for (
            member,
            subscriptions_by_product_type,
        ) in subscriptions_by_member_and_product_type.items():
            mandate_ref = get_or_create_mandate_ref(member=member, cache=cache)
            rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member, reference_date=first_of_month, cache=cache
            )
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
            for product_type, subscriptions in subscriptions_by_product_type:
                subscriptions_active_within_period = [
                    subscription
                    for subscription in subscriptions
                    if DateRangeOverlapChecker.do_ranges_overlap(
                        range_1_start=first_day_of_rhythm_period,
                        range_1_end=last_day_of_rhythm_period,
                        range_2_start=subscription.start_date,
                        range_2_end=subscription.end_date,
                    )
                ]
                existing_payments = list(
                    Payment.objects.filter(
                        mandate_ref=mandate_ref,
                        due_date__gte=first_day_of_rhythm_period,
                        due_date__lte=last_day_of_rhythm_period,
                        type=product_type.name,
                    )
                )

                already_paid = sum([payment.amount for payment in existing_payments])
                total_to_pay = sum(
                    [
                        cls.get_amount_to_pay_for_subscription_within_range(
                            subscription=subscription,
                            range_start=first_day_of_rhythm_period,
                            range_end=last_day_of_rhythm_period,
                            cache=cache,
                        )
                        for subscription in subscriptions_active_within_period
                    ]
                )

                payments_to_create.append(
                    Payment(
                        due_date=payments_due_date,
                        amount=Decimal(total_to_pay - already_paid).quantize(
                            Decimal("0.01")
                        ),
                        mandate_ref=mandate_ref,
                        status=Payment.PaymentStatus.DUE,
                        type=product_type.name,
                    )
                )

        return payments_to_create

    @classmethod
    def get_amount_to_pay_for_subscription_within_range(
        cls,
        subscription: Subscription,
        range_start: datetime.date,
        range_end: datetime.date,
        cache: dict,
    ):
        current_month = range_start
        number_of_full_month_to_pay = 0
        number_of_single_deliveries_to_pay = 0
        while current_month < range_end:
            month_is_fully_covered_by_subscription = True
            if (
                current_month == subscription.start_date.replace(day=1)
                and subscription.start_date.day != 1
            ):
                month_is_fully_covered_by_subscription = False
            if (
                current_month == subscription.end_date.replace(day=1)
                and subscription.end_date.day
                != get_last_day_of_month(subscription.end_date).day
            ):
                month_is_fully_covered_by_subscription = False

            if month_is_fully_covered_by_subscription:
                number_of_full_month_to_pay += 1
            else:
                number_of_deliveries = cls.get_number_of_deliveries_in_month(
                    subscription=subscription, first_of_month=current_month, cache=cache
                )
                if cls.should_pay_full_month_price(
                    number_of_deliveries=number_of_deliveries,
                    delivery_cycle=subscription.product.type.delivery_cycle,
                ):
                    number_of_full_month_to_pay += 1
                else:
                    number_of_single_deliveries_to_pay += number_of_deliveries

            current_month += relativedelta(months=1)

        full_months_price = (
            subscription.total_price(reference_date=range_start, cache=cache)
            * number_of_full_month_to_pay
        )
        single_deliveries_price = (
            number_of_single_deliveries_to_pay
            * DeliveryPriceCalculator.get_price_of_single_delivery_without_solidarity(
                subscription=subscription, at_date=range_start, cache=cache
            )
        )
        return full_months_price + single_deliveries_price

    @classmethod
    def should_pay_full_month_price(
        cls, number_of_deliveries: int, delivery_cycle: str
    ):
        return number_of_deliveries > cls.get_number_of_deliveries_for_full_month_price(
            delivery_cycle
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
        current_date = first_of_month
        while current_date <= last_of_month:
            current_date = DeliveryDateCalculator.get_next_delivery_date_for_delivery_cycle(
                reference_date=current_date,
                pickup_location_id=MemberPickupLocationService.get_member_pickup_location_id_from_cache(
                    member_id=subscription.member_id,
                    reference_date=current_date,
                    cache=cache,
                ),
                delivery_cycle=subscription.product.type.delivery_cycle,
                cache=cache,
            )
            if current_date <= last_of_month:
                number_of_deliveries += 1

        return number_of_deliveries

    @classmethod
    def get_payment_due_date_on_month(cls, reference_date: datetime.date, cache: dict):
        return reference_date.replace(
            day=get_parameter_value(ParameterKeys.PAYMENT_DUE_DAY, cache=cache)
        )

    @classmethod
    def group_subscriptions_by_member_and_product_type(
        cls, subscriptions: list[Subscription]
    ):
        subscriptions_by_member_and_product_type = {}
        for subscription in subscriptions:
            if (
                subscription.member
                not in subscriptions_by_member_and_product_type.keys()
            ):
                subscriptions_by_member_and_product_type[subscription.member] = {}

            subscriptions_by_product_type = subscriptions_by_member_and_product_type[
                subscription.member
            ]
            if subscription.product.type not in subscriptions_by_product_type.keys():
                subscriptions_by_product_type[subscription.product.type] = []

            subscriptions_by_product_type[subscription.product.type].append(
                subscription
            )

        return subscriptions_by_member_and_product_type

    @classmethod
    def generate_payments_for_subscriptions_in_trial(
        cls, reference_date: datetime.date, cache: dict
    ):
        raise NotImplementedError("TODO")
        return [], []

    @classmethod
    def get_number_of_deliveries_for_full_month_price(cls, delivery_cycle: str):
        if delivery_cycle == NO_DELIVERY[0]:
            return 0
        if delivery_cycle == WEEKLY[0]:
            return 4
        if delivery_cycle == ODD_WEEKS[0] or delivery_cycle == EVEN_WEEKS[0]:
            return 2
        if delivery_cycle == EVERY_FOUR_WEEKS[0]:
            return 1
        raise ImproperlyConfigured("Unknwon delivery cycle: " + delivery_cycle)
