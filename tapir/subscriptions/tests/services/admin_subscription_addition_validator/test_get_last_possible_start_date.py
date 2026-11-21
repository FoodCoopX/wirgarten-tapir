import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_subscription_addition_validator import (
    AdminSubscriptionAdditionValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(TapirCache, "get_all_growing_periods_ascending", autospec=True)
class TestAdminSubscriptionAdditionValidatorGetLastPossibleStartDate(TapirUnitTest):
    def test_getLastPossibleStartDate_severalPeriods_returnsEndDateOfTheLastOne(
        self, mock_get_all_growing_periods_ascending: MagicMock
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            GrowingPeriodFactory.build(
                start_date=datetime.date(year=2027, month=1, day=1),
                end_date=datetime.date(year=2027, month=12, day=31),
            ),
            GrowingPeriodFactory.build(
                start_date=datetime.date(year=2029, month=1, day=1),
                end_date=datetime.date(year=2029, month=12, day=31),
            ),
        ]
        cache = {}

        self.assertEqual(
            datetime.date(year=2029, month=12, day=31),
            AdminSubscriptionAdditionValidator.get_last_possible_start_date(
                cache=cache
            ),
        )
        mock_get_all_growing_periods_ascending.assert_called_once_with(cache=cache)

    def test_getLastPossibleStartDate_noPeriod_returnsNone(
        self, mock_get_all_growing_periods_ascending: MagicMock
    ):
        mock_get_all_growing_periods_ascending.return_value = []

        self.assertIsNone(
            AdminSubscriptionAdditionValidator.get_last_possible_start_date(cache={})
        )
