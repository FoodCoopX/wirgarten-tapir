import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.subscribed_products_service import (
    SubscribedProductsService,
)
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import (
    Member,
    Product,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.get_next_delivery_date import get_next_delivery_date
from tapir.wirgarten.service.products import get_next_growing_period
from tapir.wirgarten.utils import get_today


class ProductCancellationDataBuilder:
    @classmethod
    def build_data_for_all_products(cls, member: Member, cache: dict):
        return [
            cls.build_data_for_a_single_product(
                member=member, product=subscribed_product, cache=cache
            )
            for subscribed_product in SubscribedProductsService.get_subscribed_products(
                member=member, cache=cache
            )
        ]

    @classmethod
    def build_data_for_a_single_product(
        cls, member: Member, product: Product, cache: dict
    ):
        # Different cases must be handled:
        # Trial period ongoing or not
        # Notice period is in the past (= contract already renewed) or not
        # Also, is the end of the trial period after the end of the notice period

        product_subscriptions = list(
            SubscribedProductsService.get_relevant_subscriptions(
                member=member, cache=cache
            )
            .filter(product=product)
            .order_by("end_date")
        )

        is_in_trial = TrialPeriodManager.is_product_in_trial(
            product, member, cache=cache
        )
        cancellation_date = SubscriptionCancellationManager.get_earliest_possible_cancellation_date_for_product(
            product=product, member=member, cache=cache
        )
        last_subscription_end_date = product_subscriptions[-1].end_date
        date_limit_for_trial_cancellation = cls.get_date_limit_for_trial_cancellation(
            product_subscriptions=product_subscriptions, cache=cache
        )
        last_day_to_give_notice = cls.get_last_day_to_give_notice_for_product(
            product_subscriptions=product_subscriptions, cache=cache
        )

        return {
            "product": product,
            "is_in_trial": is_in_trial,
            "date_limit_for_trial_cancellation": date_limit_for_trial_cancellation,
            "cancellation_date": cancellation_date,
            "last_day_to_give_notice": last_day_to_give_notice,
            "notice_period_duration": product_subscriptions[-1].notice_period_duration,
            "notice_period_unit": product_subscriptions[-1].notice_period_unit,
            "post_trial_subscription_end_date": cls.get_post_trial_subscription_end_date(
                is_in_trial=is_in_trial,
                last_day_to_give_notice=last_day_to_give_notice,
                date_limit_for_trial_cancellation=date_limit_for_trial_cancellation,
                last_subscription_end_date=last_subscription_end_date,
                cache=cache,
            ),
        }

    @classmethod
    def get_post_trial_subscription_end_date(
        cls,
        is_in_trial: bool,
        last_day_to_give_notice: datetime.date,
        date_limit_for_trial_cancellation: datetime.date,
        last_subscription_end_date: datetime.date,
        cache: dict,
    ) -> datetime.date:
        if (
            not is_in_trial
            or last_day_to_give_notice > date_limit_for_trial_cancellation
        ):
            return last_subscription_end_date

        # This is for the case where the trial ends for example during December,
        # but the contracts get renewed on the first of December
        next_period = get_next_growing_period(
            reference_date=last_subscription_end_date, cache=cache
        )
        return (
            next_period.end_date
            if next_period is not None
            else last_subscription_end_date
        )

    @classmethod
    def get_date_limit_for_trial_cancellation(
        cls, product_subscriptions: list[Subscription], cache: dict
    ) -> datetime.date | None:
        if get_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END, cache=cache
        ):
            return cls.get_date_limit_for_trial_cancellation_flexible_mode(cache=cache)
        return cls.get_date_limit_for_trial_cancellation_fixed_mode(
            product_subscriptions=product_subscriptions, cache=cache
        )

    @classmethod
    def get_date_limit_for_trial_cancellation_flexible_mode(cls, cache: dict):
        next_delivery_date = get_next_delivery_date(cache=cache)
        date_limit = DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
            next_delivery_date, cache=cache
        )
        if date_limit >= get_today(cache=cache):
            return date_limit
        return date_limit + datetime.timedelta(days=7)

    @classmethod
    def get_date_limit_for_trial_cancellation_fixed_mode(
        cls, product_subscriptions: list[Subscription], cache: dict
    ) -> datetime.date | None:
        last_days_of_trial = [
            TrialPeriodManager.get_last_day_of_trial_period(
                contract=subscription, cache=cache
            )
            for subscription in product_subscriptions
        ]
        last_days_of_trial = [day for day in last_days_of_trial if day is not None]

        return min(last_days_of_trial, default=None)

    @classmethod
    def get_last_day_to_give_notice_for_product(
        cls, product_subscriptions: list[Subscription], cache: dict
    ):
        return max(
            NoticePeriodManager.get_max_cancellation_date_subscription(
                subscription=subscription, cache=cache
            )
            for subscription in product_subscriptions
        )
