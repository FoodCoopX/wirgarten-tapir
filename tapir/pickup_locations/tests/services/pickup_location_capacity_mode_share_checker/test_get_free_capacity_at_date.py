import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.pickup_locations.services.share_capacities_service import (
    SharesCapacityService,
)


class TestGetFreeCapacityAtDate(SimpleTestCase):
    @patch.object(
        PickupLocationCapacityModeShareChecker, "get_highest_usage_after_date"
    )
    @patch.object(
        SharesCapacityService,
        "get_available_share_capacities_for_pickup_location_by_product_type",
    )
    def test_getFreeCapacityAtDate_default_returnsDifferenceBetweenAvailableCapacityAndHighestFutureUsage(
        self,
        mock_get_available_share_capacities_for_pickup_location_by_product_type: Mock,
        mock_get_highest_usage_after_date: Mock,
    ):
        product_type = Mock()
        pickup_location = Mock()
        reference_date = datetime.date(year=2022, month=7, day=19)
        mock_get_available_share_capacities_for_pickup_location_by_product_type.return_value = {
            product_type: 10
        }
        mock_get_highest_usage_after_date.return_value = 7
        cache = {}

        result = PickupLocationCapacityModeShareChecker.get_free_capacity_at_date(
            product_type=product_type,
            pickup_location=pickup_location,
            reference_date=reference_date,
            cache=cache,
        )

        self.assertEqual(3, result)

        mock_get_available_share_capacities_for_pickup_location_by_product_type.assert_called_once_with(
            pickup_location=pickup_location,
            cache=cache,
        )
        mock_get_highest_usage_after_date.assert_called_once_with(
            pickup_location=pickup_location,
            product_type=product_type,
            reference_date=reference_date,
            cache=cache,
        )
