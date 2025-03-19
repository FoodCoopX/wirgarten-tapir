import datetime

from dateutil.relativedelta import relativedelta

from tapir.wirgarten.models import Subscription
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

        return cls.get_end_of_trial_period(subscription) > reference_date
