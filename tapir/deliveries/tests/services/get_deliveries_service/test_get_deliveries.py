import datetime

from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.wirgarten.constants import WEEKLY, ODD_WEEKS
from tapir.wirgarten.models import ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import mock_timezone, TapirIntegrationTest


class TestGetDeliveriesServiceGetDeliveries(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.product = ProductFactory.create(type__delivery_cycle=WEEKLY[0])
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1)
        )
        GrowingPeriodFactory.create(start_date=datetime.date(year=2025, month=1, day=1))

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime(year=2023, month=3, day=15))

        self.member = MemberFactory.create()
        SubscriptionFactory.create(
            member=self.member, product=self.product, period=self.growing_period
        )

    def test_getDeliveries_default_buildsDeliveryForAllDatesBetweenFromAndTo(self):

        cache = {}
        actual_deliveries = GetDeliveriesService.get_deliveries(
            member=self.member,
            date_from=datetime.date(year=2024, month=4, day=1),
            date_to=datetime.date(year=2024, month=4, day=30),
            cache=cache,
        )

        self.assertEqual(4, len(actual_deliveries))
        expected_delivery_dates = [
            datetime.date(year=2024, month=4, day=day) for day in [3, 10, 17, 24]
        ]
        for index, actual_delivery in enumerate(actual_deliveries):
            self.assertEqual(
                expected_delivery_dates[index], actual_delivery["delivery_date"]
            )

    def test_getDeliveries_noDeliveryOnSomeDays_returnedListContainsOnlyDeliveredDays(
        self,
    ):
        ProductType.objects.update(delivery_cycle=ODD_WEEKS[0])

        cache = {}
        actual_deliveries = GetDeliveriesService.get_deliveries(
            member=self.member,
            date_from=datetime.date(year=2024, month=4, day=1),
            date_to=datetime.date(year=2024, month=4, day=30),
            cache=cache,
        )

        self.assertEqual(2, len(actual_deliveries))
        expected_delivery_dates = [
            datetime.date(year=2024, month=4, day=day) for day in [10, 24]
        ]
        for index, actual_delivery in enumerate(actual_deliveries):
            self.assertEqual(
                expected_delivery_dates[index], actual_delivery["delivery_date"]
            )

    def test_getDeliveries_dateRangeIncludesNextGrowingPeriod_returnsDeliveriesForPlannedRenewedSubscriptions(
        self,
    ):
        cache = {}
        self._set_parameter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, value=True
        )

        deliveries = GetDeliveriesService.get_deliveries(
            member=self.member,
            date_from=datetime.date(year=2024, month=4, day=1),
            date_to=datetime.date(year=2025, month=4, day=30),
            cache=cache,
        )

        self.assertEqual(57, len(deliveries))
