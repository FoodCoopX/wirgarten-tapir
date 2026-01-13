import datetime

from tapir.pickup_locations.services.pickup_location_opening_times_manager import (
    PickupLocationOpeningTimesManager,
)
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestUpdateDeliveryDateToOpeningTimes(TapirIntegrationTest):
    def test_updateDeliveryDateToOpeningTimes_default_movesDateToFirstDayWithOpening(
        self,
    ):
        pickup_location = PickupLocationFactory.create()
        for day_of_week in [2, 3, 4]:
            PickupLocationOpeningTime.objects.create(
                pickup_location=pickup_location,
                day_of_week=day_of_week,
                open_time=datetime.time(hour=8),
                close_time=datetime.time(hour=9),
            )

        self.assertEqual(
            datetime.date(year=2025, month=3, day=5),
            PickupLocationOpeningTimesManager.update_delivery_date_to_opening_times(
                list(PickupLocationOpeningTime.objects.all()),
                datetime.date(year=2025, month=3, day=3),
            ),
        )

        self.assertEqual(
            datetime.date(year=2025, month=3, day=5),
            PickupLocationOpeningTimesManager.update_delivery_date_to_opening_times(
                list(PickupLocationOpeningTime.objects.all()),
                datetime.date(year=2025, month=3, day=7),
            ),
        )

    def test_updateDeliveryDateToOpeningTimes_noOpeningTimes_returnsSameDay(
        self,
    ):
        self.assertEqual(
            datetime.date(year=2025, month=3, day=5),
            PickupLocationOpeningTimesManager.update_delivery_date_to_opening_times(
                [],
                datetime.date(year=2025, month=3, day=5),
            ),
        )
