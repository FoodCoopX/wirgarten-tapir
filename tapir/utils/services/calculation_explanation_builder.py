from decimal import Decimal

from tapir.utils.dataclasses import CalculationPart
from tapir.wirgarten.utils import format_currency


class CalculationExplanationBuilder:
    @classmethod
    def build_lines(
        cls, calculation_parts: list[CalculationPart], total: Decimal
    ) -> list[str]:
        lines = [part.explanation for part in calculation_parts]
        lines.append(f"Summe: {format_currency(total)} €")
        return lines

    @classmethod
    def build_credit_lines(
        cls, calculation_parts: list[CalculationPart], total: Decimal
    ) -> list[str]:
        return [
            "Berechnung der Gutschrift:",
            *cls.build_lines(calculation_parts=calculation_parts, total=total),
        ]
