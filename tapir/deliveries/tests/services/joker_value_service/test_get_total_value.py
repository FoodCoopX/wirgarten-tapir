from decimal import Decimal

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.utils.dataclasses import CalculationPart
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetTotalValue(TapirUnitTest):
    def test_getTotalValue_positiveParts_returnsSum(self):
        parts = [
            CalculationPart(explanation="", value=Decimal("2.5")),
            CalculationPart(explanation="", value=Decimal("1.25")),
        ]

        self.assertEqual(Decimal("3.75"), JokerValueService.get_total_value(parts))

    def test_getTotalValue_negativePartLowersTotal_returnsSum(self):
        parts = [
            CalculationPart(explanation="", value=Decimal("2.5")),
            CalculationPart(explanation="", value=Decimal("-1")),
        ]

        self.assertEqual(Decimal("1.5"), JokerValueService.get_total_value(parts))

    def test_getTotalValue_sumIsNegative_returnsZero(self):
        parts = [
            CalculationPart(explanation="", value=Decimal("2.5")),
            CalculationPart(explanation="", value=Decimal("-4")),
        ]

        self.assertEqual(Decimal(0), JokerValueService.get_total_value(parts))
