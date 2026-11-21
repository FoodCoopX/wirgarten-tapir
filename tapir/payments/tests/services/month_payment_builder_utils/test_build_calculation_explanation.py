from decimal import Decimal

from tapir.utils.dataclasses import CalculationPart
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildCalculationExplanation(TapirUnitTest):
    PARTS = [
        CalculationPart(explanation="Oktober 2026, A", value=Decimal(152)),
        CalculationPart(explanation="Oktober 2026, B", value=Decimal(32)),
    ]

    def test_buildCalculationExplanation_nothingPaidYet_showsPartsAndSum(self):
        self.assertEqual(
            "Oktober 2026, A\nOktober 2026, B\nSumme: 184,00 €",
            MonthPaymentBuilderUtils._build_calculation_explanation(
                calculation_parts=self.PARTS,
                total_to_pay=Decimal(184),
                already_paid=Decimal(0),
            ),
        )

    def test_buildCalculationExplanation_somethingAlreadyPaid_showsAlreadyPaidAndDifference(
        self,
    ):
        self.assertEqual(
            "Oktober 2026, A\nOktober 2026, B\nSumme: 184,00 €\nBereits bezahlt: 190,00 €\nZu zahlen: -6,00 €",
            MonthPaymentBuilderUtils._build_calculation_explanation(
                calculation_parts=self.PARTS,
                total_to_pay=Decimal(184),
                already_paid=Decimal(190),
            ),
        )
