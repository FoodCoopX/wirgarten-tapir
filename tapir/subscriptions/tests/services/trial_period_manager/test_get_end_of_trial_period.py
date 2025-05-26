import datetime
from unittest.mock import Mock, patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from tapir.subscriptions.config import (
    NOTICE_PERIOD_UNIT_MONTHS,
    NOTICE_PERIOD_UNIT_WEEKS,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestGetEndOfTrialPeriod(SimpleTestCase):
    def test_getEndOfTrialPeriod_trialDisabled_returnsNone(self):
        subscription = Mock()
        subscription.trial_disabled = True
        cache = {}

        result = TrialPeriodManager.get_end_of_trial_period(subscription, cache=cache)

        self.assertIsNone(result)

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    def test_getEndOfTrialPeriod_trialEndDateIsOverridden_returnsOverride(
        self, mock_get_parameter_value: Mock
    ):
        subscription = Mock()
        subscription.trial_disabled = False
        trial_end_date_override = Mock()
        subscription.trial_end_date_override = trial_end_date_override
        mock_get_parameter_value.return_value = True
        cache = {}

        result = TrialPeriodManager.get_end_of_trial_period(subscription, cache=cache)

        self.assertEqual(trial_end_date_override, result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        )

    @patch.object(TrialPeriodManager, "get_end_of_trial_period_by_months")
    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    def test_getEndOfTrialPeriod_trialPeriodDurationIsInMonths_callsCorrectFunction(
        self,
        mock_get_parameter_value: Mock,
        mock_get_end_of_trial_period_by_months: Mock,
    ):
        subscription = Mock()
        subscription.trial_disabled = False
        subscription.trial_end_date_override = None
        mock_get_parameter_value.side_effect = lambda key, cache: {
            ParameterKeys.TRIAL_PERIOD_ENABLED: True,
            ParameterKeys.TRIAL_PERIOD_UNIT: NOTICE_PERIOD_UNIT_MONTHS,
        }[key]
        end_of_trial_period_by_months = Mock()
        mock_get_end_of_trial_period_by_months.return_value = (
            end_of_trial_period_by_months
        )
        cache = {}

        result = TrialPeriodManager.get_end_of_trial_period(subscription, cache=cache)

        self.assertEqual(end_of_trial_period_by_months, result)
        mock_get_end_of_trial_period_by_months.assert_called_once_with(
            subscription, cache=cache
        )

    @patch.object(TrialPeriodManager, "get_end_of_trial_period_by_weeks")
    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    def test_getEndOfTrialPeriod_trialPeriodDurationIsInMonths_callsCorrectFunction(
        self,
        mock_get_parameter_value: Mock,
        mock_get_end_of_trial_period_by_weeks: Mock,
    ):
        subscription = Mock()
        subscription.trial_disabled = False
        subscription.trial_end_date_override = None
        mock_get_parameter_value.side_effect = lambda key, cache: {
            ParameterKeys.TRIAL_PERIOD_ENABLED: True,
            ParameterKeys.TRIAL_PERIOD_UNIT: NOTICE_PERIOD_UNIT_WEEKS,
        }[key]
        end_of_trial_period_by_weeks = Mock()
        mock_get_end_of_trial_period_by_weeks.return_value = (
            end_of_trial_period_by_weeks
        )
        cache = {}

        result = TrialPeriodManager.get_end_of_trial_period(subscription, cache=cache)

        self.assertEqual(end_of_trial_period_by_weeks, result)
        mock_get_end_of_trial_period_by_weeks.assert_called_once_with(
            subscription, cache=cache
        )

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    def test_getEndOfTrialPeriod_trialPeriodDurationIsUnknownUnit_raisesException(
        self,
        mock_get_parameter_value: Mock,
    ):
        subscription = Mock()
        subscription.trial_disabled = False
        subscription.trial_end_date_override = None
        mock_get_parameter_value.side_effect = lambda key, cache: {
            ParameterKeys.TRIAL_PERIOD_ENABLED: True,
            ParameterKeys.TRIAL_PERIOD_UNIT: "invalid",
        }[key]
        cache = {}

        with self.assertRaises(ImproperlyConfigured):
            TrialPeriodManager.get_end_of_trial_period(subscription, cache=cache)

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    def test_getEndOfTrialPeriodByMonths_durationIsOneMonth_returnsCorrectDate(
        self,
        mock_get_parameter_value: Mock,
    ):
        subscription = Mock()
        subscription.start_date = datetime.date(year=2025, month=1, day=1)
        mock_get_parameter_value.return_value = 1
        cache = {}

        result = TrialPeriodManager.get_end_of_trial_period_by_months(
            subscription, cache=cache
        )

        self.assertEqual(datetime.date(year=2025, month=2, day=1), result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_DURATION, cache=cache
        )

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    def test_getEndOfTrialPeriodByMonths_durationIsTwoMonth_returnsCorrectDate(
        self,
        mock_get_parameter_value: Mock,
    ):
        subscription = Mock()
        subscription.start_date = datetime.date(year=2025, month=3, day=16)
        mock_get_parameter_value.return_value = 2
        cache = {}

        result = TrialPeriodManager.get_end_of_trial_period_by_months(
            subscription, cache=cache
        )

        self.assertEqual(datetime.date(year=2025, month=5, day=16), result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_DURATION, cache=cache
        )

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    def test_getEndOfTrialPeriodByWeeks_durationIsOneWeek_returnsCorrectDate(
        self,
        mock_get_parameter_value: Mock,
    ):
        subscription = Mock()
        subscription.start_date = datetime.date(year=2025, month=1, day=1)
        mock_get_parameter_value.return_value = 1
        cache = {}

        result = TrialPeriodManager.get_end_of_trial_period_by_weeks(
            subscription, cache=cache
        )

        self.assertEqual(datetime.date(year=2025, month=1, day=8), result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_DURATION, cache=cache
        )

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    def test_getEndOfTrialPeriodByWeeks_durationIs5Week_returnsCorrectDate(
        self,
        mock_get_parameter_value: Mock,
    ):
        subscription = Mock()
        subscription.start_date = datetime.date(year=2025, month=5, day=6)
        mock_get_parameter_value.return_value = 5
        cache = {}

        result = TrialPeriodManager.get_end_of_trial_period_by_weeks(
            subscription, cache=cache
        )

        self.assertEqual(datetime.date(year=2025, month=6, day=10), result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_DURATION, cache=cache
        )
