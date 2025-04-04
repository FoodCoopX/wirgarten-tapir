import datetime
from unittest.mock import Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager


class TestGetEndOfTrialPeriod(SimpleTestCase):
    def test_getEndOfTrialPeriod_trialDisabled_returnsDateBeforeSubscriptionStart(self):
        subscription = Mock()
        subscription.trial_disabled = True
        start_date = datetime.date(year=2026, month=2, day=5)
        subscription.start_date = start_date

        result = TrialPeriodManager.get_end_of_trial_period(subscription)

        self.assertLess(result, start_date)

    def test_getEndOfTrialPeriod_trialEndDateIsContainedInSubscription_returnsDateFromSubscription(
        self,
    ):
        subscription = Mock()
        subscription.trial_disabled = False
        trial_end_date_override = Mock()
        subscription.trial_end_date_override = trial_end_date_override

        result = TrialPeriodManager.get_end_of_trial_period(subscription)

        self.assertEqual(trial_end_date_override, result)

    def test_getEndOfTrialPeriod_trialEndDateIsNotOverriden_returnsEndOfMonthRelativeToStartDate(
        self,
    ):
        subscription = Mock()
        subscription.trial_disabled = False
        start_date = datetime.date(year=2026, month=2, day=5)
        subscription.start_date = start_date
        subscription.trial_end_date_override = None

        result = TrialPeriodManager.get_end_of_trial_period(subscription)

        self.assertEqual(datetime.date(year=2026, month=2, day=28), result)
