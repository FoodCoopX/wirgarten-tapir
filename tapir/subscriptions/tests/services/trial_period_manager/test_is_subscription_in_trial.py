import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestIsSubscriptionInTrial(SimpleTestCase):
    def setUp(self):
        mock_timezone(self, datetime.datetime(year=2026, month=3, day=15))

    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_isSubscriptionInTrial_endOfTrialIsInThePast_returnsFalse(
        self, mock_get_end_of_trial_period: Mock
    ):
        mock_get_end_of_trial_period.return_value = datetime.date(
            year=2026, month=2, day=28
        )
        subscription = Mock()
        subscription.cancellation_ts = None

        result = TrialPeriodManager.is_subscription_in_trial(subscription)

        self.assertFalse(result)
        mock_get_end_of_trial_period.assert_called_once_with(subscription)

    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_isSubscriptionInTrial_endOfTrialIsInTheFuture_returnsTrue(
        self, mock_get_end_of_trial_period: Mock
    ):
        mock_get_end_of_trial_period.return_value = datetime.date(
            year=2026, month=3, day=31
        )
        subscription = Mock()
        subscription.cancellation_ts = None

        result = TrialPeriodManager.is_subscription_in_trial(subscription)

        self.assertTrue(result)
        mock_get_end_of_trial_period.assert_called_once_with(subscription)

    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_isSubscriptionInTrial_endOfTrialIsOnSameDay_returnsTrue(
        self, mock_get_end_of_trial_period: Mock
    ):
        mock_get_end_of_trial_period.return_value = datetime.date(
            year=2026, month=3, day=15
        )
        subscription = Mock()
        subscription.cancellation_ts = None

        result = TrialPeriodManager.is_subscription_in_trial(subscription)

        self.assertTrue(result)
        mock_get_end_of_trial_period.assert_called_once_with(subscription)

    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_isSubscriptionInTrial_subscriptionHasBeenCancelled_returnsFalse(
        self, mock_get_end_of_trial_period: Mock
    ):
        mock_get_end_of_trial_period.return_value = datetime.date(
            year=2026, month=3, day=15
        )
        subscription = Mock()
        subscription.cancellation_ts = datetime.datetime(year=2026, month=3, day=15)

        result = TrialPeriodManager.is_subscription_in_trial(subscription)

        self.assertFalse(result)
        mock_get_end_of_trial_period.assert_not_called()
