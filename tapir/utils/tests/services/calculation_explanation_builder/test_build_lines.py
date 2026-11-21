from decimal import Decimal

from tapir.utils.dataclasses import CalculationPart
from tapir.utils.services.calculation_explanation_builder import (
    CalculationExplanationBuilder,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildLines(TapirUnitTest):
    def test_buildLines_default_returnsOneLinePerPartAndTotal(self):
        result = CalculationExplanationBuilder.build_lines(
            calculation_parts=[
                CalculationPart(explanation="Part A", value=Decimal("4.528")),
                CalculationPart(explanation="Part B", value=Decimal("1.5")),
            ],
            total=Decimal("6.028"),
        )

        self.assertEqual(["Part A", "Part B", "Summe: 6,03 €"], result)

    def test_buildLines_noParts_returnsOnlyTotal(self):
        result = CalculationExplanationBuilder.build_lines(
            calculation_parts=[], total=Decimal(0)
        )

        self.assertEqual(["Summe: 0,00 €"], result)
