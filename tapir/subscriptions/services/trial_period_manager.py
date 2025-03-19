import datetime

from dateutil.relativedelta import relativedelta

from tapir.wirgarten.models import Subscription


class TrialPeriodManager:
    @classmethod
    def get_end_of_trial_period(cls, subscription: Subscription):
        if subscription.trial_disabled:
            return subscription.start_date - datetime.timedelta(days=1)

        if subscription.trial_end_date_override is not None:
            return subscription.trial_end_date_override

        return subscription.start_date + relativedelta(months=1, day=1, days=-1)
