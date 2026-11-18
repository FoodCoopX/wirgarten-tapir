import datetime
from decimal import Decimal

from tapir.utils.dataclasses import CalculationPart
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetCalculationPartsForSingleContributionWithinRange(TapirUnitTest):
    def test_getCalculationPartsForSingleContributionWithinRange_contributionIsNotWithinRange_returnsEmptyList(
        self,
    ):
        contribution = SolidarityContributionFactory.build(
            amount=Decimal(100), start_date=datetime.date(year=1992, month=4, day=1)
        )

        result = MonthPaymentBuilderSolidarityContributions._get_calculation_parts_for_single_contribution_within_range(
            range_start=datetime.date(year=1992, month=1, day=1),
            range_end=datetime.date(year=1992, month=3, day=31),
            contribution=contribution,
        )

        self.assertEqual([], result)

    def test_getCalculationPartsForSingleContributionWithinRange_default_returnsOnePartPerCoveredMonth(
        self,
    ):
        contribution = SolidarityContributionFactory.build(
            amount=Decimal(100), start_date=datetime.date(year=1993, month=2, day=15)
        )

        result = MonthPaymentBuilderSolidarityContributions._get_calculation_parts_for_single_contribution_within_range(
            range_start=datetime.date(year=1993, month=1, day=1),
            range_end=datetime.date(year=1993, month=3, day=31),
            contribution=contribution,
        )

        self.assertEqual(
            [
                CalculationPart(
                    explanation="Februar 1993, Solidarbeitrag: 100,00 € × 14 von 28 Tagen = 50,00 €",
                    value=Decimal("50.00"),
                ),
                CalculationPart(
                    explanation="März 1993, Solidarbeitrag: 100,00 € monatlich (voller Monat)",
                    value=Decimal(100),
                ),
            ],
            result,
        )
