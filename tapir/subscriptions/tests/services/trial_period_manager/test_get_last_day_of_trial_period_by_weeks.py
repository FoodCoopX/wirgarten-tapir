import datetime
from unittest.mock import Mock, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestGetLastDayOfTrialPeriodByWeeks(TapirUnitTest):
    @patch.object(TrialPeriodManager, "get_trial_period_start_date", autospec=True)
    @patch(
        "tapir.subscriptions.services.trial_period_manager.get_parameter_value",
        autospec=True,
    )
    def test_getLastDayOfTrialPeriodByWeeks_durationIsOneWeek_returnsCorrectDate(
        self,
        mock_get_parameter_value: Mock,
        mock_get_trial_period_start_date: Mock,
    ):
        subscription = Mock()
        subscription.start_date = datetime.date(year=2025, month=1, day=1)
        mock_get_parameter_value.return_value = 1
        mock_get_trial_period_start_date.return_value = datetime.date(
            year=2025, month=1, day=13
        )
        cache = {}

        result = TrialPeriodManager.get_last_day_of_trial_period_by_weeks(
            subscription, cache=cache
        )

        self.assertEqual(datetime.date(year=2025, month=1, day=19), result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_DURATION, cache=cache
        )

    @patch.object(TrialPeriodManager, "get_trial_period_start_date", autospec=True)
    @patch(
        "tapir.subscriptions.services.trial_period_manager.get_parameter_value",
        autospec=True,
    )
    def test_getLastDayOfTrialPeriodByWeeks_durationIs5Week_returnsCorrectDate(
        self,
        mock_get_parameter_value: Mock,
        mock_get_trial_period_start_date: Mock,
    ):
        subscription = Mock()
        subscription.start_date = datetime.date(year=2025, month=5, day=6)
        mock_get_parameter_value.return_value = 5
        mock_get_trial_period_start_date.return_value = datetime.date(
            year=2025, month=6, day=16
        )
        cache = {}

        result = TrialPeriodManager.get_last_day_of_trial_period_by_weeks(
            subscription, cache=cache
        )

        self.assertEqual(datetime.date(year=2025, month=7, day=20), result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_DURATION, cache=cache
        )
