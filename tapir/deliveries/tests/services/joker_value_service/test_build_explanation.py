from decimal import Decimal

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.utils.dataclasses import CalculationPart
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildExplanation(TapirUnitTest):
    def test_buildExplanation_default_listsEachPartAndTotal(self):
        parts = [
            CalculationPart(explanation="Part A", value=Decimal("4.528")),
            CalculationPart(explanation="Part B", value=Decimal("1.5")),
        ]

        self.assertEqual(
            "Berechnung der Gutschrift:\nPart A\nPart B\nSumme: 6,03 €",
            JokerValueService.build_explanation(parts),
        )

    def test_buildExplanation_sumIsNegative_totalIsZero(self):
        parts = [
            CalculationPart(explanation="Part A", value=Decimal("2")),
            CalculationPart(explanation="Part B", value=Decimal("-3")),
        ]

        self.assertEqual(
            "Berechnung der Gutschrift:\nPart A\nPart B\nSumme: 0,00 €",
            JokerValueService.build_explanation(parts),
        )
