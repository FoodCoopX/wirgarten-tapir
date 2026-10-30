import datetime
from decimal import Decimal

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.wirgarten.constants import WEEKLY, ODD_WEEKS, EVERY_FOUR_WEEKS
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildMonthlyToDeliveryCalculation(TapirUnitTest):
    def test_buildMonthlyToDeliveryCalculation_weekly_noCycleFactor(self):
        self.assertEqual(
            "10,00 € monatlich × 12 ÷ 52 Wochen",
            JokerValueService._build_monthly_to_delivery_calculation(
                monthly_amount=Decimal(10),
                delivery_cycle=WEEKLY[0],
                joker_date=datetime.date(year=2021, month=5, day=7),
            ),
        )

    def test_buildMonthlyToDeliveryCalculation_everyTwoWeeks_showsFactorTwo(self):
        self.assertEqual(
            "10,00 € monatlich × 12 ÷ 53 Wochen × 2 (Lieferung alle 2 Wochen)",
            JokerValueService._build_monthly_to_delivery_calculation(
                monthly_amount=Decimal(10),
                delivery_cycle=ODD_WEEKS[0],
                joker_date=datetime.date(year=2020, month=5, day=7),
            ),
        )

    def test_buildMonthlyToDeliveryCalculation_everyFourWeeks_showsFactorFour(self):
        self.assertEqual(
            "-5,50 € monatlich × 12 ÷ 52 Wochen × 4 (Lieferung alle 4 Wochen)",
            JokerValueService._build_monthly_to_delivery_calculation(
                monthly_amount=Decimal("-5.5"),
                delivery_cycle=EVERY_FOUR_WEEKS[0],
                joker_date=datetime.date(year=2021, month=5, day=7),
            ),
        )
