import datetime
from unittest.mock import Mock, patch

from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetDefaultTrialEndDateForAdminEnable(TapirUnitTest):
    @patch(
        "tapir.subscriptions.services.trial_period_manager.get_parameter_value",
        autospec=True,
    )
    def test_getDefaultTrialEndDateForAdminEnable_trialGloballyDisabled_returnsNone(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = False
        subscription = Mock()
        cache = {}

        result = TrialPeriodManager.get_default_trial_end_date_for_admin_enable(
            subscription, cache=cache
        )

        self.assertIsNone(result)

    @patch(
        "tapir.subscriptions.services.trial_period_manager.get_today",
        autospec=True,
    )
    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        TrialPeriodManager, "get_last_day_of_trial_period_by_weeks", autospec=True
    )
    @patch.object(
        TrialPeriodManager,
        "get_last_day_of_trial_period_by_weeks_from_reference",
        autospec=True,
    )
    @patch(
        "tapir.subscriptions.services.trial_period_manager.get_parameter_value",
        autospec=True,
    )
    def test_getDefaultTrialEndDateForAdminEnable_expiredTrial_returnsEndFromToday(
        self,
        mock_get_parameter_value: Mock,
        mock_get_last_day_from_reference: Mock,
        mock_get_last_day_by_weeks: Mock,
        mock_is_contract_in_trial: Mock,
        mock_get_today: Mock,
    ):
        mock_get_parameter_value.return_value = True
        mock_is_contract_in_trial.return_value = False
        today = datetime.date(2026, 7, 3)
        mock_get_today.return_value = today
        contract_start_end = datetime.date(2026, 2, 1)
        expected_date = datetime.date(2026, 8, 2)
        mock_get_last_day_by_weeks.return_value = contract_start_end
        mock_get_last_day_from_reference.return_value = expected_date
        subscription = Mock()
        cache = {}

        result = TrialPeriodManager.get_default_trial_end_date_for_admin_enable(
            subscription, cache=cache
        )

        self.assertEqual(expected_date, result)
        mock_get_last_day_from_reference.assert_called_once_with(
            subscription, today, cache=cache
        )
