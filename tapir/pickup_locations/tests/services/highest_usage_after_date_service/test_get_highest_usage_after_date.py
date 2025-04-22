import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.pickup_locations.services.highest_usage_after_date_service import (
    HighestUsageAfterDateService,
)


class TestGetHighestUsageAfterDate(SimpleTestCase):
    @patch.object(
        HighestUsageAfterDateService,
        "get_date_of_last_possible_capacity_change",
    )
    def test_getHighestUsageAfterDate_default_returnsHighestUsage(
        self,
        mock_get_date_of_last_possible_capacity_change: Mock,
    ):
        mock_get_date_of_last_possible_capacity_change.return_value = datetime.date(
            year=2025, month=3, day=23
        )

        pickup_location = Mock()
        cache = {}

        lambda_get_usage_at_date = Mock()
        lambda_get_usage_at_date.side_effect = [5, 12, 10]

        result = HighestUsageAfterDateService.get_highest_usage_after_date_generic(
            pickup_location=pickup_location,
            reference_date=datetime.date(year=2025, month=3, day=4),
            lambda_get_usage_at_date=lambda_get_usage_at_date,
            cache=cache,
        )

        self.assertEqual(12, result)

        mock_get_date_of_last_possible_capacity_change.assert_called_once_with(
            cache=cache, pickup_location=pickup_location
        )
        self.assertEqual(3, lambda_get_usage_at_date.call_count)
        lambda_get_usage_at_date.assert_has_calls(
            [
                call(
                    reference_date,
                )
                for reference_date in [
                    # check for the reference date then all following mondays before the limit
                    datetime.date(year=2025, month=3, day=4),
                    datetime.date(year=2025, month=3, day=10),
                    datetime.date(year=2025, month=3, day=17),
                ]
            ],
            any_order=True,
        )
