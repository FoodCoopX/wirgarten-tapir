import datetime

from tapir.deliveries.models import DeliveryDayAdjustment
from tapir.deliveries.services.member_specific_delivery_day_calculator import (
    MemberSpecificDeliveryDayCalculator,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationOpeningTimesFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberSpecificDeliveryDayCalculator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getSpecificDeliveryDate_noPickupLocation_returnsSameDateAsInput(self):
        member = MemberFactory.create()

        result = MemberSpecificDeliveryDayCalculator.get_specific_delivery_date(
            member_id=member.id,
            delivery_date=datetime.date(year=2020, month=11, day=18),
            cache={},
        )

        self.assertEqual(datetime.date(year=2020, month=11, day=18), result)

    def test_getSpecificDeliveryDate_pickupLocationWithoutOpeningTimes_returnsSameDateAsInput(
        self,
    ):
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member, valid_from=datetime.date(year=2020, month=1, day=1)
        )

        result = MemberSpecificDeliveryDayCalculator.get_specific_delivery_date(
            member_id=member.id,
            delivery_date=datetime.date(year=2020, month=11, day=18),
            cache={},
        )

        self.assertEqual(datetime.date(year=2020, month=11, day=18), result)

    def test_getSpecificDeliveryDate_pickupLocationWithOpeningTimes_returnsDateAdjustedToPickupLocation(
        self,
    ):
        member = MemberFactory.create()
        member_pickup_location = MemberPickupLocationFactory.create(
            member=member, valid_from=datetime.date(year=2020, month=1, day=1)
        )
        PickupLocationOpeningTimesFactory.create(
            pickup_location=member_pickup_location.pickup_location, day_of_week=4
        )

        result = MemberSpecificDeliveryDayCalculator.get_specific_delivery_date(
            member_id=member.id,
            delivery_date=datetime.date(year=2020, month=11, day=18),
            cache={},
        )

        self.assertEqual(datetime.date(year=2020, month=11, day=20), result)

    def test_getSpecificDeliveryDate_bothPickupLocationAndAdjustedDelivery_adjustedDeliveryHasPriority(
        self,
    ):
        member = MemberFactory.create()
        member_pickup_location = MemberPickupLocationFactory.create(
            member=member, valid_from=datetime.date(year=2020, month=1, day=1)
        )
        PickupLocationOpeningTimesFactory.create(
            pickup_location=member_pickup_location.pickup_location, day_of_week=4
        )
        DeliveryDayAdjustment.objects.create(
            growing_period=GrowingPeriodFactory.create(
                start_date=datetime.date(year=2020, month=1, day=1)
            ),
            calendar_week=47,
            adjusted_weekday=1,
        )

        result = MemberSpecificDeliveryDayCalculator.get_specific_delivery_date(
            member_id=member.id,
            delivery_date=datetime.date(year=2020, month=11, day=18),
            cache={},
        )

        self.assertEqual(datetime.date(year=2020, month=11, day=17), result)
