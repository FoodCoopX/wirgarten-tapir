import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)


class TestGetHighestUsageAfterDate(SimpleTestCase):

    @patch.object(PickupLocationCapacityModeShareChecker, "get_capacity_usage_at_date")
    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "get_date_of_last_possible_capacity_change",
    )
    def test_getHighestUsageAfterDate_default_returnsHighestUsage(
        self,
        mock_get_date_of_last_possible_capacity_change: Mock,
        mock_get_capacity_usage_at_date: Mock,
    ):
        mock_get_date_of_last_possible_capacity_change.return_value = datetime.date(
            year=2025, month=3, day=23
        )
        mock_get_capacity_usage_at_date.side_effect = [5, 12, 10]

        pickup_location = Mock()
        product_type = Mock()
        cache = {}

        result = PickupLocationCapacityModeShareChecker.get_highest_usage_after_date(
            pickup_location=pickup_location,
            product_type=product_type,
            reference_date=datetime.date(year=2025, month=3, day=4),
            cache=cache,
        )

        self.assertEqual(12, result)

        mock_get_date_of_last_possible_capacity_change.assert_called_once_with(
            pickup_location
        )
        self.assertEqual(3, mock_get_capacity_usage_at_date.call_count)
        mock_get_capacity_usage_at_date.assert_has_calls(
            [
                call(
                    pickup_location=pickup_location,
                    product_type=product_type,
                    reference_date=reference_date,
                    cache=cache,
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
