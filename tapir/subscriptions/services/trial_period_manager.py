import datetime
from typing import Dict

from dateutil.relativedelta import relativedelta

from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.wirgarten.models import Subscription, Product, Member
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import get_today


class TrialPeriodManager:
    @classmethod
    def get_end_of_trial_period(cls, subscription: Subscription):
        if subscription.trial_disabled:
            return subscription.start_date - datetime.timedelta(days=1)

        if subscription.trial_end_date_override is not None:
            return subscription.trial_end_date_override

        return subscription.start_date + relativedelta(months=1, day=1, days=-1)

    @classmethod
    def is_subscription_in_trial(
        cls, subscription: Subscription, reference_date: datetime.date | None = None
    ) -> bool:
        if reference_date is None:
            reference_date = get_today()

        return cls.get_end_of_trial_period(subscription) >= reference_date

    @classmethod
    def get_earliest_trial_cancellation_date(
        cls, reference_date: datetime.date | None = None, cache: Dict = None
    ) -> datetime.date:
        if reference_date is None:
            reference_date = get_today()

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
        reference_date: datetime.date | None = None,
    ) -> bool:
        if reference_date is None:
            reference_date = get_today()

        subscriptions = get_active_and_future_subscriptions().filter(
            member=member, product=product
        )
        for subscription in subscriptions:
            if cls.is_subscription_in_trial(subscription, reference_date):
                return True
        return False
