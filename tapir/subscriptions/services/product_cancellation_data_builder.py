import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
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
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_today


class ProductCancellationDataBuilder:
    @classmethod
    def build_data_for_all_products(cls, member: Member, cache: dict):
        return [
            cls.build_data_for_a_single_product(
                member=member, product=subscribed_product, cache=cache
            )
            for subscribed_product in cls.get_subscribed_products(
                member=member, cache=cache
            )
        ]

    @classmethod
    def build_data_for_a_single_product(
        cls, member: Member, product: Product, cache: dict
    ):
        product_subscriptions = list(
            cls.get_relevant_subscriptions(member=member, cache=cache)
            .filter(product=product)
            .order_by("end_date")
        )

        return {
            "product": product,
            "is_in_trial": TrialPeriodManager.is_product_in_trial(
                product, member, cache=cache
            ),
            "date_limit_for_trial_cancellation": cls.get_date_limit_for_trial_cancellation(
                product_subscriptions=product_subscriptions, cache=cache
            ),
            "cancellation_date": SubscriptionCancellationManager.get_earliest_possible_cancellation_date_for_product(
                product=product, member=member, cache=cache
            ),
            "last_day_of_notice_period": cls.get_last_day_of_notice_period_for_product(
                product_subscriptions=product_subscriptions, cache=cache
            ),
            "notice_period_duration": product_subscriptions[-1].notice_period_duration,
            "notice_period_unit": product_subscriptions[-1].notice_period_unit,
            "subscription_end_date": product_subscriptions[-1].end_date,
        }

    @classmethod
    def get_date_limit_for_trial_cancellation(
        cls, product_subscriptions: list[Subscription], cache: dict
    ):
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
    ):
        end_of_trial_period = min(
            TrialPeriodManager.get_last_day_of_trial_period(
                contract=subscription, cache=cache
            )
            for subscription in product_subscriptions
        )
        return DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
            end_of_trial_period, cache=cache
        )

    @classmethod
    def get_last_day_of_notice_period_for_product(
        cls, product_subscriptions: list[Subscription], cache: dict
    ):
        return max(
            NoticePeriodManager.get_max_cancellation_date_subscription(
                subscription=subscription, cache=cache
            )
            for subscription in product_subscriptions
        )

    @classmethod
    def get_subscribed_products(cls, member: Member, cache: dict):
        return {
            subscription.product
            for subscription in cls.get_relevant_subscriptions(
                member=member, cache=cache
            ).select_related("product")
        }

    @classmethod
    def get_relevant_subscriptions(cls, member: Member, cache: dict):
        return get_active_and_future_subscriptions(cache=cache).filter(
            member=member, cancellation_ts__isnull=True
        )
