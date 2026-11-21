import datetime
from decimal import Decimal

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildProportionalCalculation(TapirUnitTest):
    def test_buildProportionalCalculation_severalDates_pluralAndMonthName(self):
        self.assertEqual(
            "95,00 € monatlich ÷ 5 Liefertermine im Oktober",
            JokerValueService._build_proportional_calculation(
                monthly_amount=Decimal(95),
                number_of_dates=5,
                month=datetime.date(year=2026, month=10, day=8),
            ),
        )

    def test_buildProportionalCalculation_singleDate_singular(self):
        self.assertEqual(
            "95,00 € monatlich ÷ 1 Liefertermin im Februar",
            JokerValueService._build_proportional_calculation(
                monthly_amount=Decimal(95),
                number_of_dates=1,
                month=datetime.date(year=2026, month=2, day=4),
            ),
        )
