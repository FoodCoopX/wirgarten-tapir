import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)


class TestGetFreeCapacityAtDate(SimpleTestCase):
    @patch.object(
        PickupLocationCapacityModeBasketChecker, "get_highest_usage_after_date"
    )
    @patch.object(
        BasketSizeCapacitiesService,
        "get_basket_size_capacities_for_pickup_location",
    )
    def test_getFreeCapacityAtDate_default_returnsDifferenceBetweenAvailableCapacityAndHighestFutureUsage(
        self,
        mock_get_basket_size_capacities_for_pickup_location: Mock,
        mock_get_highest_usage_after_date: Mock,
    ):
        pickup_location = Mock()
        reference_date = datetime.date(year=2022, month=7, day=19)
        mock_get_basket_size_capacities_for_pickup_location.return_value = {
            "test_size": 10
        }
        mock_get_highest_usage_after_date.return_value = 7
        cache = {}

        result = PickupLocationCapacityModeBasketChecker.get_free_capacity_at_date(
            pickup_location=pickup_location,
            basket_size="test_size",
            reference_date=reference_date,
            cache=cache,
        )

        self.assertEqual(3, result)

        mock_get_basket_size_capacities_for_pickup_location.assert_called_once_with(
            pickup_location, cache=cache
        )
        mock_get_highest_usage_after_date.assert_called_once_with(
            basket_size="test_size",
            pickup_location=pickup_location,
            reference_date=reference_date,
            cache=cache,
        )
