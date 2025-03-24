import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestGetEarliestTrialCancellationDate(SimpleTestCase):
    def setUp(self):
        mock_timezone(self, datetime.datetime(year=2027, month=6, day=4))

    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
    )
    @patch("tapir.subscriptions.services.trial_period_manager.get_next_delivery_date")
    def test_getEarliestTrialCancellationDate_dateLimitIsAfterInputDate_returnsInputDate(
        self,
        mock_get_next_delivery_date: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
    ):
        next_delivery_date = Mock()
        mock_get_next_delivery_date.return_value = next_delivery_date
        date_limit = datetime.date(year=2027, month=6, day=5)
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = date_limit

        result = TrialPeriodManager.get_earliest_trial_cancellation_date()

        self.assertEqual(datetime.date(year=2027, month=6, day=4), result)

    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
    )
    @patch("tapir.subscriptions.services.trial_period_manager.get_next_delivery_date")
    def test_getEarliestTrialCancellationDate_dateLimitIsSayDayAsInputDate_returnsInputDate(
        self,
        mock_get_next_delivery_date: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
    ):
        next_delivery_date = Mock()
        mock_get_next_delivery_date.return_value = next_delivery_date
        date_limit = datetime.date(year=2027, month=6, day=4)
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = date_limit

        result = TrialPeriodManager.get_earliest_trial_cancellation_date()

        self.assertEqual(datetime.date(year=2027, month=6, day=4), result)

    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
    )
    @patch("tapir.subscriptions.services.trial_period_manager.get_next_delivery_date")
    def test_getEarliestTrialCancellationDate_dateLimitIsBeforeInputDate_returnsDayAfterNextDelivery(
        self,
        mock_get_next_delivery_date: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
    ):
        next_delivery_date = datetime.date(year=2027, month=6, day=10)
        mock_get_next_delivery_date.return_value = next_delivery_date
        date_limit = datetime.date(year=2027, month=6, day=3)
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = date_limit

        result = TrialPeriodManager.get_earliest_trial_cancellation_date()

        self.assertEqual(datetime.date(year=2027, month=6, day=11), result)
