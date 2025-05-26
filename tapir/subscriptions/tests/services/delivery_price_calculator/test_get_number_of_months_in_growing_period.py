import datetime

from django.test import SimpleTestCase

from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestGetNumberOfMonthsInGrowingPeriod(SimpleTestCase):
    def test_getNumberOfMonthsInGrowingPeriod_default_returnsCorrectNumberOfMonth(self):
        self.assertEqual(
            12,
            DeliveryPriceCalculator.get_number_of_months_in_growing_period(
                GrowingPeriodFactory.build(
                    start_date=datetime.date(year=2024, month=1, day=1),
                    end_date=datetime.date(year=2024, month=12, day=31),
                )
            ),
        )

        self.assertEqual(
            1,
            DeliveryPriceCalculator.get_number_of_months_in_growing_period(
                GrowingPeriodFactory.build(
                    start_date=datetime.date(year=2024, month=1, day=1),
                    end_date=datetime.date(year=2024, month=1, day=31),
                )
            ),
        )

        self.assertEqual(
            24,
            DeliveryPriceCalculator.get_number_of_months_in_growing_period(
                GrowingPeriodFactory.build(
                    start_date=datetime.date(year=2024, month=1, day=1),
                    end_date=datetime.date(year=2025, month=12, day=31),
                )
            ),
        )

        self.assertEqual(
            30,
            DeliveryPriceCalculator.get_number_of_months_in_growing_period(
                GrowingPeriodFactory.build(
                    start_date=datetime.date(year=2024, month=1, day=1),
                    end_date=datetime.date(year=2026, month=6, day=30),
                )
            ),
        )
