import datetime

from tapir.deliveries.models import DeliveryDayAdjustment
from tapir.deliveries.services.pickup_location_delivery_date_calculator import (
    PickupLocationDeliveryDateCalculator,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PickupLocationFactory,
    PickupLocationOpeningTimesFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationDeliveryDateCalculator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getDeliveryDateAtPickupLocation_noPickupLocation_returnsSameDateAsInput(
        self,
    ):
        result = (
            PickupLocationDeliveryDateCalculator.get_delivery_date_at_pickup_location(
                pickup_location_id=None,
                delivery_date=datetime.date(year=2020, month=11, day=18),  # Wednesday
                cache={},
            )
        )

        self.assertEqual(
            datetime.date(year=2020, month=11, day=18),  # Wednesday
            result,
        )

    def test_getDeliveryDateAtPickupLocation_pickupLocationWithoutOpeningTimes_returnsSameDateAsInput(
        self,
    ):
        pickup_location = PickupLocationFactory.create()

        result = (
            PickupLocationDeliveryDateCalculator.get_delivery_date_at_pickup_location(
                pickup_location_id=pickup_location.id,
                delivery_date=datetime.date(year=2020, month=11, day=18),  # Wednesday
                cache={},
            )
        )

        self.assertEqual(
            datetime.date(year=2020, month=11, day=18),  # Wednesday
            result,
        )

    def test_getDeliveryDateAtPickupLocation_pickupLocationWithOpeningTimes_returnsDateAdjustedToPickupLocation(
        self,
    ):
        pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTimesFactory.create(
            pickup_location=pickup_location, day_of_week=4  # Friday
        )

        result = (
            PickupLocationDeliveryDateCalculator.get_delivery_date_at_pickup_location(
                pickup_location_id=pickup_location.id,
                delivery_date=datetime.date(year=2020, month=11, day=18),  # Wednesday
                cache={},
            )
        )

        self.assertEqual(datetime.date(year=2020, month=11, day=20), result)  # Friday

    def test_getDeliveryDateAtPickupLocation_bothOpeningTimesAndAdjustedDelivery_adjustedDeliveryHasPriority(
        self,
    ):
        pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTimesFactory.create(
            pickup_location=pickup_location, day_of_week=4  # Friday
        )
        DeliveryDayAdjustment.objects.create(
            growing_period=GrowingPeriodFactory.create(
                start_date=datetime.date(year=2020, month=1, day=1)
            ),
            calendar_week=47,
            adjusted_weekday=1,  # Tuesday
        )

        result = (
            PickupLocationDeliveryDateCalculator.get_delivery_date_at_pickup_location(
                pickup_location_id=pickup_location.id,
                delivery_date=datetime.date(year=2020, month=11, day=18),  # Wednesday
                cache={},
            )
        )

        self.assertEqual(datetime.date(year=2020, month=11, day=17), result)  # Tuesday
