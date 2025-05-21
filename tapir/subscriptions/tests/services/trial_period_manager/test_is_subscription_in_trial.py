import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestIsSubscriptionInTrial(SimpleTestCase):
    def setUp(self):
        mock_timezone(self, datetime.datetime(year=2026, month=3, day=15))

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_isSubscriptionInTrial_endOfTrialIsInThePast_returnsFalse(
        self, mock_get_end_of_trial_period: Mock, mock_get_parameter_value: Mock
    ):
        mock_get_end_of_trial_period.return_value = datetime.date(
            year=2026, month=2, day=28
        )
        subscription = Mock()
        subscription.cancellation_ts = None
        mock_get_parameter_value.return_value = True
        cache = {}

        result = TrialPeriodManager.is_subscription_in_trial(subscription, cache=cache)

        self.assertFalse(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        )
        mock_get_end_of_trial_period.assert_called_once_with(subscription, cache=cache)

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_isSubscriptionInTrial_endOfTrialIsInTheFuture_returnsTrue(
        self, mock_get_end_of_trial_period: Mock, mock_get_parameter_value: Mock
    ):
        mock_get_end_of_trial_period.return_value = datetime.date(
            year=2026, month=3, day=31
        )
        subscription = Mock()
        subscription.cancellation_ts = None
        mock_get_parameter_value.return_value = True
        cache = {}

        result = TrialPeriodManager.is_subscription_in_trial(subscription, cache=cache)

        self.assertTrue(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        )
        mock_get_end_of_trial_period.assert_called_once_with(subscription, cache=cache)

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_isSubscriptionInTrial_endOfTrialIsOnSameDay_returnsTrue(
        self, mock_get_end_of_trial_period: Mock, mock_get_parameter_value: Mock
    ):
        mock_get_end_of_trial_period.return_value = datetime.date(
            year=2026, month=3, day=15
        )
        subscription = Mock()
        subscription.cancellation_ts = None
        mock_get_parameter_value.return_value = True
        cache = {}

        result = TrialPeriodManager.is_subscription_in_trial(subscription, cache=cache)

        self.assertTrue(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        )
        mock_get_end_of_trial_period.assert_called_once_with(subscription, cache=cache)

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_isSubscriptionInTrial_subscriptionHasBeenCancelled_returnsFalse(
        self, mock_get_end_of_trial_period: Mock, mock_get_parameter_value: Mock
    ):
        mock_get_end_of_trial_period.return_value = datetime.date(
            year=2026, month=3, day=15
        )
        subscription = Mock()
        subscription.cancellation_ts = datetime.datetime(year=2026, month=3, day=15)
        mock_get_parameter_value.return_value = True
        cache = {}

        result = TrialPeriodManager.is_subscription_in_trial(subscription, cache=cache)

        self.assertFalse(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        )
        mock_get_end_of_trial_period.assert_not_called()

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_isSubscriptionInTrial_trialPeriodsAreDisabled_returnsFalse(
        self, mock_get_end_of_trial_period: Mock, mock_get_parameter_value: Mock
    ):
        mock_get_end_of_trial_period.return_value = datetime.date(
            year=2026, month=3, day=31
        )
        subscription = Mock()
        subscription.cancellation_ts = None
        mock_get_parameter_value.return_value = False
        cache = {}

        result = TrialPeriodManager.is_subscription_in_trial(subscription, cache=cache)

        self.assertFalse(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        )
        mock_get_end_of_trial_period.assert_not_called()
