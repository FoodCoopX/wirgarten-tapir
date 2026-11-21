from decimal import Decimal

from tapir.utils.dataclasses import CalculationPart
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildExplanation(TapirUnitTest):
    def test_buildExplanation_default_showsPartsSumAlreadyPaidAndCredit(self):
        result = MemberCreditCreator._build_explanation(
            calculation_parts=[
                CalculationPart(
                    explanation="Oktober 2026, Ernteanteil Kiste: 95,00 € × 4 ÷ 5 Liefertermine = 76,00 €",
                    value=Decimal(76),
                )
            ],
            total_to_pay=Decimal(76),
            already_paid=Decimal(95),
            amount_to_credit=Decimal(19),
        )

        self.assertEqual(
            "Berechnung der Gutschrift:\n"
            "Oktober 2026, Ernteanteil Kiste: 95,00 € × 4 ÷ 5 Liefertermine = 76,00 €\n"
            "Summe: 76,00 €\n"
            "Bereits bezahlt: 95,00 €\n"
            "Gutschrift: 19,00 €",
            result,
        )
