import datetime
from decimal import Decimal

from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.constants import WEEKLY, ODD_WEEKS, EVERY_FOUR_WEEKS
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetPriceOfSingleDeliveryFromMonthlyPrice(TapirUnitTest):
    def get_price(self, monthly_price: Decimal, delivery_cycle: str, year: int):
        return DeliveryPriceCalculator.get_price_of_single_delivery_from_monthly_price(
            monthly_price=monthly_price,
            delivery_cycle=delivery_cycle,
            at_date=datetime.date(year=year, month=5, day=7),
        ).quantize(Decimal("0.01"))

    def test_getPriceOfSingleDeliveryFromMonthlyPrice_weekly_returnsMonthlyPriceSpreadOverWeeks(
        self,
    ):
        # 10 * 12 / 52
        self.assertEqual(
            Decimal("2.31"),
            self.get_price(
                monthly_price=Decimal(10), delivery_cycle=WEEKLY[0], year=2021
            ),
        )

    def test_getPriceOfSingleDeliveryFromMonthlyPrice_yearWith53Weeks_dividesBy53(
        self,
    ):
        # 10 * 12 / 53
        self.assertEqual(
            Decimal("2.26"),
            self.get_price(
                monthly_price=Decimal(10), delivery_cycle=WEEKLY[0], year=2020
            ),
        )

    def test_getPriceOfSingleDeliveryFromMonthlyPrice_everyTwoWeeks_returnsDoublePrice(
        self,
    ):
        # 10 * 12 / 52 * 2
        self.assertEqual(
            Decimal("4.62"),
            self.get_price(
                monthly_price=Decimal(10), delivery_cycle=ODD_WEEKS[0], year=2021
            ),
        )

    def test_getPriceOfSingleDeliveryFromMonthlyPrice_everyFourWeeks_returnsQuadruplePrice(
        self,
    ):
        # 10 * 12 / 52 * 4
        self.assertEqual(
            Decimal("9.23"),
            self.get_price(
                monthly_price=Decimal(10), delivery_cycle=EVERY_FOUR_WEEKS[0], year=2021
            ),
        )

    def test_getPriceOfSingleDeliveryFromMonthlyPrice_negativeAmount_returnsNegativePrice(
        self,
    ):
        # -5 * 12 / 52
        self.assertEqual(
            Decimal("-1.15"),
            self.get_price(
                monthly_price=Decimal(-5), delivery_cycle=WEEKLY[0], year=2021
            ),
        )
