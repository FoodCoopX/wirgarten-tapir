from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestGetLastDayOfTrialPeriod(SimpleTestCase):
    def test_getLastDayOfTrialPeriod_trialDisabled_returnsNone(self):
        subscription = Mock()
        subscription.trial_disabled = True
        cache = {}

        result = TrialPeriodManager.get_last_day_of_trial_period(
            subscription, cache=cache
        )

        self.assertIsNone(result)

    @patch(
        "tapir.subscriptions.services.trial_period_manager.get_parameter_value",
        autospec=True,
    )
    def test_getLastDayOfTrialPeriod_trialEndDateIsOverridden_returnsOverride(
        self, mock_get_parameter_value: Mock
    ):
        subscription = Mock()
        subscription.trial_disabled = False
        trial_end_date_override = Mock()
        subscription.trial_end_date_override = trial_end_date_override
        mock_get_parameter_value.return_value = True
        cache = {}

        result = TrialPeriodManager.get_last_day_of_trial_period(
            subscription, cache=cache
        )

        self.assertEqual(trial_end_date_override, result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        )

    @patch.object(
        TrialPeriodManager, "get_last_day_of_trial_period_by_weeks", autospec=True
    )
    @patch(
        "tapir.subscriptions.services.trial_period_manager.get_parameter_value",
        autospec=True,
    )
    def test_getLastDayOfTrialPeriod_trialPeriodDurationIsInWeeks_callsCorrectFunction(
        self,
        mock_get_parameter_value: Mock,
        mock_get_last_day_of_trial_period_by_weeks: Mock,
    ):
        subscription = Mock()
        subscription.trial_disabled = False
        subscription.trial_end_date_override = None
        mock_get_parameter_value.side_effect = lambda key, cache: {
            ParameterKeys.TRIAL_PERIOD_ENABLED: True,
        }[key]
        end_of_trial_period_by_weeks = Mock()
        mock_get_last_day_of_trial_period_by_weeks.return_value = (
            end_of_trial_period_by_weeks
        )
        cache = {}

        result = TrialPeriodManager.get_last_day_of_trial_period(
            subscription, cache=cache
        )

        self.assertEqual(end_of_trial_period_by_weeks, result)
        mock_get_last_day_of_trial_period_by_weeks.assert_called_once_with(
            subscription, cache=cache
        )
