import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestGetEarliestTrialCancellationDate(SimpleTestCase):
    def setUp(self):
        self.today = mock_timezone(
            self, datetime.datetime(year=2027, month=6, day=4)
        ).date()

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
    )
    @patch("tapir.subscriptions.services.trial_period_manager.get_next_delivery_date")
    def test_getEarliestTrialCancellationDate_dateLimitIsAfterInputDate_returnsInputDate(
        self,
        mock_get_next_delivery_date: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
        mock_get_parameter_value: Mock,
    ):
        next_delivery_date = Mock()
        mock_get_next_delivery_date.return_value = next_delivery_date
        date_limit = datetime.date(year=2027, month=6, day=5)
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = date_limit
        cache = {}
        subscription = Mock()
        mock_get_parameter_value.return_value = True

        result = TrialPeriodManager.get_earliest_trial_cancellation_date(
            subscription, cache=cache
        )

        self.assertEqual(self.today, result)
        mock_get_next_delivery_date.assert_called_once_with(self.today, cache=cache)
        mock_calculate_date_limit_for_delivery_changes_in_week.assert_called_once_with(
            next_delivery_date, cache=cache
        )
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END, cache=cache
        )

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
    )
    @patch("tapir.subscriptions.services.trial_period_manager.get_next_delivery_date")
    def test_getEarliestTrialCancellationDate_dateLimitIsSayDayAsInputDate_returnsInputDate(
        self,
        mock_get_next_delivery_date: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
        mock_get_parameter_value: Mock,
    ):
        next_delivery_date = Mock()
        mock_get_next_delivery_date.return_value = next_delivery_date
        date_limit = datetime.date(year=2027, month=6, day=4)
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = date_limit
        cache = {}
        subscription = Mock()
        mock_get_parameter_value.return_value = True

        result = TrialPeriodManager.get_earliest_trial_cancellation_date(
            subscription, cache=cache
        )

        self.assertEqual(self.today, result)
        mock_get_next_delivery_date.assert_called_once_with(self.today, cache=cache)
        mock_calculate_date_limit_for_delivery_changes_in_week.assert_called_once_with(
            next_delivery_date, cache=cache
        )
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END, cache=cache
        )

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
    )
    @patch("tapir.subscriptions.services.trial_period_manager.get_next_delivery_date")
    def test_getEarliestTrialCancellationDate_dateLimitIsBeforeInputDate_returnsDayAfterNextDelivery(
        self,
        mock_get_next_delivery_date: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
        mock_get_parameter_value: Mock,
    ):
        next_delivery_date = datetime.date(year=2027, month=6, day=10)
        mock_get_next_delivery_date.return_value = next_delivery_date
        date_limit = datetime.date(year=2027, month=6, day=3)
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = date_limit
        subscription = Mock()
        mock_get_parameter_value.return_value = True
        cache = {}

        result = TrialPeriodManager.get_earliest_trial_cancellation_date(
            subscription, cache=cache
        )

        self.assertEqual(datetime.date(year=2027, month=6, day=11), result)
        mock_get_next_delivery_date.assert_called_once_with(self.today, cache=cache)
        mock_calculate_date_limit_for_delivery_changes_in_week.assert_called_once_with(
            next_delivery_date, cache=cache
        )
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END, cache=cache
        )

    @patch("tapir.subscriptions.services.trial_period_manager.get_parameter_value")
    @patch.object(
        TrialPeriodManager,
        "get_end_of_trial_period",
    )
    def test_getEarliestTrialCancellationDate_trialCannotBeCancelledEarly_returnsEndOfTrial(
        self,
        mock_get_end_of_trial_period: Mock,
        mock_get_parameter_value: Mock,
    ):
        subscription = Mock()
        mock_get_parameter_value.return_value = False
        end_of_trial_period = datetime.date(year=2027, month=6, day=11)
        mock_get_end_of_trial_period.return_value = end_of_trial_period
        cache = {}

        result = TrialPeriodManager.get_earliest_trial_cancellation_date(
            subscription, cache=cache
        )

        self.assertEqual(datetime.date(year=2027, month=6, day=11), result)
        mock_get_end_of_trial_period.assert_called_once_with(subscription, cache=cache)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END, cache=cache
        )
