import datetime
from typing import Dict

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.subscriptions.config import (
    NOTICE_PERIOD_UNIT_MONTHS,
    NOTICE_PERIOD_UNIT_WEEKS,
)
from tapir.wirgarten.models import Subscription, Product, Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
    get_active_subscriptions,
)
from tapir.wirgarten.utils import get_today


class TrialPeriodManager:
    @classmethod
    def get_end_of_trial_period(cls, subscription: Subscription, cache: Dict):
        if subscription.trial_disabled or not get_parameter_value(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        ):
            return None

        if subscription.trial_end_date_override is not None:
            return subscription.trial_end_date_override

        unit = get_parameter_value(ParameterKeys.TRIAL_PERIOD_UNIT, cache=cache)
        if unit == NOTICE_PERIOD_UNIT_MONTHS:
            return cls.get_end_of_trial_period_by_months(subscription, cache=cache)
        if unit == NOTICE_PERIOD_UNIT_WEEKS:
            return cls.get_end_of_trial_period_by_weeks(subscription, cache=cache)

        raise ImproperlyConfigured(f"Unknown trial period unit: {unit}")

    @classmethod
    def get_end_of_trial_period_by_months(cls, subscription: Subscription, cache: Dict):
        return subscription.start_date + relativedelta(
            months=get_parameter_value(ParameterKeys.TRIAL_PERIOD_DURATION, cache=cache)
        )

    @classmethod
    def get_end_of_trial_period_by_weeks(cls, subscription: Subscription, cache: Dict):
        return subscription.start_date + relativedelta(
            weeks=get_parameter_value(ParameterKeys.TRIAL_PERIOD_DURATION, cache=cache)
        )

    @classmethod
    def is_subscription_in_trial(
        cls,
        subscription: Subscription,
        reference_date: datetime.date = None,
        cache: Dict = None,
    ) -> bool:
        if not get_parameter_value(ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache):
            return False

        if reference_date is None:
            reference_date = get_today(cache=cache)

        if subscription.cancellation_ts is not None:
            return False

        end_of_trial_period = cls.get_end_of_trial_period(subscription, cache=cache)
        if end_of_trial_period is None:
            return False

        return end_of_trial_period >= reference_date

    @classmethod
    def get_earliest_trial_cancellation_date(
        cls,
        subscription: Subscription,
        reference_date: datetime.date | None = None,
        cache: Dict = None,
    ) -> datetime.date:
        if not get_parameter_value(
            ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END, cache=cache
        ):
            return cls.get_end_of_trial_period(subscription, cache=cache)

        if reference_date is None:
            reference_date = get_today(cache=cache)

        next_delivery_date = get_next_delivery_date(reference_date, cache=cache)
        date_limit = DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
            next_delivery_date, cache=cache
        )
        if date_limit >= reference_date:
            return reference_date

        return next_delivery_date + datetime.timedelta(days=1)

    @classmethod
    def is_product_in_trial(
        cls,
        product: Product,
        member: Member,
        cache: Dict,
        reference_date: datetime.date | None = None,
    ) -> bool:
        if not get_parameter_value(ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache):
            return False

        if reference_date is None:
            reference_date = get_today(cache=cache)

        return cls.is_subscription_in_trial(
            get_active_and_future_subscriptions(
                reference_date=reference_date, cache=cache
            )
            .filter(member=member, product=product)
            .order_by("start_date")
            .first(),
            reference_date,
        )

    @classmethod
    def get_subscriptions_in_trial_period(
        cls, member_id: str, reference_date: datetime.date = None, cache: Dict = None
    ) -> list[Subscription]:
        if not get_parameter_value(ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache):
            return []

        subscriptions = get_active_subscriptions(cache=cache).filter(
            member_id=member_id,
        )

        return list(
            filter(
                lambda subscription: cls.is_subscription_in_trial(
                    subscription, reference_date=reference_date, cache=cache
                ),
                subscriptions,
            )
        )
