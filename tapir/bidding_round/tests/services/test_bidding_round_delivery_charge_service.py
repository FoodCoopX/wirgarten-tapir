import datetime
from decimal import Decimal

from tapir.configuration.models import TapirParameter
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.pickup_locations.tests.factories import PickupLocationDeliveryChargeFactory
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    PickupLocationFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundDeliveryChargeService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value="2")
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value=True
        )

        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        cls.pickup_location = PickupLocationFactory.create()
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=cls.pickup_location,
            valid_from=datetime.date(year=2026, month=1, day=1),
            amount=Decimal("1.50"),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=cls.pickup_location,
            day_of_week=2,
            open_time=datetime.time(hour=14),
            close_time=datetime.time(hour=18),
        )
        cls.product_type = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])

    def test_getYearlyDeliveryCharge_weeklyDelivery_returnsChargeTimesDeliveries(
        self,
    ):
        result = BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
            pickup_location_id=self.pickup_location.id,
            product_type=self.product_type,
            growing_period=self.growing_period,
            cache={},
        )

        self.assertEqual(Decimal("1.50") * 52, result)

    def test_getYearlyDeliveryCharge_withoutPickupLocation_returnsZero(self):
        result = BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
            pickup_location_id=None,
            product_type=self.product_type,
            growing_period=self.growing_period,
            cache={},
        )

        self.assertEqual(Decimal("0.00"), result)

    def test_getYearlyDeliveryCharge_withoutCharge_returnsZero(self):
        other_location = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=other_location,
            day_of_week=2,
            open_time=datetime.time(hour=14),
            close_time=datetime.time(hour=18),
        )

        result = BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
            pickup_location_id=other_location.id,
            product_type=self.product_type,
            growing_period=self.growing_period,
            cache={},
        )

        self.assertEqual(Decimal("0.00"), result)
