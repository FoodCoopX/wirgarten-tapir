from decimal import Decimal

from tapir.deliveries.services.joker_value_service import (
    JokerValueService,
    JokerCreditValuePart,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildExplanation(TapirUnitTest):
    def test_buildExplanation_default_listsEachPartAndTotal(self):
        parts = [
            JokerCreditValuePart(explanation="Part A", value=Decimal("4.528")),
            JokerCreditValuePart(explanation="Part B", value=Decimal("1.5")),
        ]

        self.assertEqual(
            "Berechnung der Gutschrift:\n- Part A\n- Part B\nSumme: 6,03 €",
            JokerValueService.build_explanation(parts),
        )

    def test_buildExplanation_sumIsNegative_totalIsZero(self):
        parts = [
            JokerCreditValuePart(explanation="Part A", value=Decimal("2")),
            JokerCreditValuePart(explanation="Part B", value=Decimal("-3")),
        ]

        self.assertEqual(
            "Berechnung der Gutschrift:\n- Part A\n- Part B\nSumme: 0,00 €",
            JokerValueService.build_explanation(parts),
        )
