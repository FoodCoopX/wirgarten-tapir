import datetime

from tapir.configuration.models import TapirParameter
from tapir.deliveries.models import DeliveryDayAdjustment
from tapir.deliveries.services.delivery_day_adjustment_service import (
    DeliveryDayAdjustmentService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDeliveryDayAdjustmentService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getAdjustedDeliveryWeekday_noGrowingPeriod_returnsDefaultWeekday(self):
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value=5)

        result = DeliveryDayAdjustmentService.get_adjusted_delivery_weekday(
            datetime.date.today(), cache={}
        )

        self.assertEqual(5, result)

    def test_getAdjustedDeliveryWeekday_noAdjustmentInWeek_returnsDefaultWeekday(self):
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value=5)
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        DeliveryDayAdjustment.objects.create(
            growing_period=growing_period, calendar_week=2, adjusted_weekday=3
        )

        result = DeliveryDayAdjustmentService.get_adjusted_delivery_weekday(
            datetime.date(year=2023, month=6, day=4), cache={}
        )

        self.assertEqual(5, result)

    def test_getAdjustedDeliveryWeekday_hasAdjustmentInWeek_returnsAdjustedWeekday(
        self,
    ):
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value=5)
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        DeliveryDayAdjustment.objects.create(
            growing_period=growing_period, calendar_week=2, adjusted_weekday=3
        )

        result = DeliveryDayAdjustmentService.get_adjusted_delivery_weekday(
            datetime.date(year=2023, month=1, day=12), cache={}
        )

        self.assertEqual(3, result)
