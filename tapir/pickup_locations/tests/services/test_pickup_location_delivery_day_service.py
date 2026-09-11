import datetime

from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationDeliveryDayService(TapirIntegrationTest):
    @staticmethod
    def _add_opening_time(pickup_location, day_of_week):
        return PickupLocationOpeningTime.objects.create(
            pickup_location=pickup_location,
            day_of_week=day_of_week,
            open_time=datetime.time(9, 0),
            close_time=datetime.time(18, 0),
        )

    def test_getDeliveryDay_severalOpeningDays_returnsTheEarliest(self):
        pickup_location = PickupLocationFactory.create()
        self._add_opening_time(pickup_location, 4)
        self._add_opening_time(pickup_location, 1)

        self.assertEqual(
            PickupLocationDeliveryDayService.get_delivery_day(
                pickup_location_id=pickup_location.id, cache={}
            ),
            1,
        )

    def test_getDeliveryDay_openingDayIsMonday_returnsZero(self):
        # 0 is falsy: the accessor must distinguish it from "no opening times".
        pickup_location = PickupLocationFactory.create()
        self._add_opening_time(pickup_location, 0)

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
        # This is the point of the service: the property it replaces issued one
        # query per access, and every caller reads it inside a loop.
        pickup_locations = []
        for day_of_week in range(5):
            pickup_location = PickupLocationFactory.create()
            self._add_opening_time(pickup_location, day_of_week)
            pickup_locations.append(pickup_location)

        cache = {}
        with self.assertNumQueries(1):
            delivery_days = [
                PickupLocationDeliveryDayService.get_delivery_day(
                    pickup_location_id=pickup_location.id, cache=cache
                )
                for pickup_location in pickup_locations
            ]

        self.assertEqual(delivery_days, [0, 1, 2, 3, 4])
