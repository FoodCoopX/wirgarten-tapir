import datetime
from unittest.mock import Mock

from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.constants import NO_DELIVERY, WEEKLY, EVEN_WEEKS, ODD_WEEKS
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetNumberOfDeliveriesInGrowingPeriod(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_getNumberOfDeliveriesInGrowingPeriod_deliveryCycleIsNoDeliveries_returns0(
        self,
    ):
        result = DeliveryPriceCalculator.get_number_of_deliveries_in_growing_period(
            Mock(), NO_DELIVERY[0]
        )

        self.assertEqual(0, result)

    def test_getNumberOfDeliveriesInGrowingPeriod_deliveryCycleIsWeekly_returnsTotalNumberOfWeeks(
        self,
    ):
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=2, day=28),
        )
        result = DeliveryPriceCalculator.get_number_of_deliveries_in_growing_period(
            growing_period, WEEKLY[0]
        )

        self.assertEqual(9, result)

    def test_getNumberOfDeliveriesInGrowingPeriod_deliveryCycleIsEven_returnsCorrectNumberOfWeeks(
        self,
    ):
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=2, day=28),
        )
        result = DeliveryPriceCalculator.get_number_of_deliveries_in_growing_period(
            growing_period, EVEN_WEEKS[0]
        )

        self.assertEqual(4, result)

    def test_getNumberOfDeliveriesInGrowingPeriod_deliveryCycleIsOdd_returnsCorrectNumberOfWeeks(
        self,
    ):
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=2, day=28),
        )
        result = DeliveryPriceCalculator.get_number_of_deliveries_in_growing_period(
            growing_period, ODD_WEEKS[0]
        )

        self.assertEqual(5, result)
