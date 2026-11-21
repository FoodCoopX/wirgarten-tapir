from decimal import Decimal
from unittest.mock import patch, MagicMock

from tapir.utils.dataclasses import CalculationPart
from tapir.utils.services.calculation_explanation_builder import (
    CalculationExplanationBuilder,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildCreditLines(TapirUnitTest):
    @patch.object(
        CalculationExplanationBuilder,
        "build_lines",
        autospec=True,
        return_value=["Part A", "Summe: 4,53 €"],
    )
    def test_buildCreditLines_default_returnsHeaderFollowedByLines(
        self, mock_build_lines: MagicMock
    ):
        calculation_parts = [
            CalculationPart(explanation="Part A", value=Decimal("4.53"))
        ]

        result = CalculationExplanationBuilder.build_credit_lines(
            calculation_parts=calculation_parts, total=Decimal("4.53")
        )

        self.assertEqual(
            ["Berechnung der Gutschrift:", "Part A", "Summe: 4,53 €"], result
        )
        mock_build_lines.assert_called_once_with(
            calculation_parts=calculation_parts, total=Decimal("4.53")
        )
