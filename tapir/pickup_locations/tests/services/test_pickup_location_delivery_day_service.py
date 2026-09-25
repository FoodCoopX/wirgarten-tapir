from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationDeliveryDayService(TapirIntegrationTest):
    def test_getDeliveryDay_severalOpeningDays_returnsTheEarliest(self):
        pickup_location = create_pickup_location_with_opening_times([4, 1])

        self.assertEqual(
            PickupLocationDeliveryDayService.get_delivery_day(
                pickup_location_id=pickup_location.id, cache={}
            ),
            1,
        )

    def test_getDeliveryDay_openingDayIsMonday_returnsZero(self):
        pickup_location = create_pickup_location_with_opening_times([0])

        self.assertEqual(
            PickupLocationDeliveryDayService.get_delivery_day(
                pickup_location_id=pickup_location.id, cache={}
            ),
            0,
        )

    def test_getDeliveryDay_noOpeningTimes_returnsNone(self):
        pickup_location = PickupLocationFactory.create()

        self.assertIsNone(
            PickupLocationDeliveryDayService.get_delivery_day(
                pickup_location_id=pickup_location.id, cache={}
            )
        )

    def test_getDeliveryDay_noPickupLocationId_returnsNone(self):
        self.assertIsNone(
            PickupLocationDeliveryDayService.get_delivery_day(
                pickup_location_id=None, cache={}
            )
        )

    def test_getDeliveryDay_manyLocationsOneCache_costsASingleQuery(self):
        pickup_locations = [
            create_pickup_location_with_opening_times([day_of_week])
            for day_of_week in range(5)
        ]

        cache = {}
        with self.assertNumQueries(1):
            delivery_days = [
                PickupLocationDeliveryDayService.get_delivery_day(
                    pickup_location_id=pickup_location.id, cache=cache
                )
                for pickup_location in pickup_locations
            ]

        self.assertEqual(delivery_days, [0, 1, 2, 3, 4])
