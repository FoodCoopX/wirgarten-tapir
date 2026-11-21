import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, call

from tapir.utils.dataclasses import CalculationPart
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetCalculationParts(TapirUnitTest):
    @patch.object(
        MonthPaymentBuilderSolidarityContributions,
        "_get_calculation_parts_for_single_contribution_within_range",
        autospec=True,
    )
    def test_getCalculationParts_default_returnsPartsOfActiveContributionsSortedByStartDate(
        self, mock_get_calculation_parts_for_single_contribution_within_range: MagicMock
    ):
        contribution_starting_later = SolidarityContributionFactory.build(
            start_date=datetime.date(year=1990, month=6, day=1),
            end_date=datetime.date(year=1990, month=12, day=31),
        )
        contribution_starting_earlier = SolidarityContributionFactory.build(
            start_date=datetime.date(year=1990, month=2, day=1),
            end_date=datetime.date(year=1990, month=5, day=31),
        )
        contribution_inactive = SolidarityContributionFactory.build(
            start_date=datetime.date(year=1989, month=1, day=1),
            end_date=datetime.date(year=1989, month=12, day=31),
        )
        parts_by_contribution = {
            contribution_starting_later: [
                CalculationPart(explanation="later", value=Decimal(1))
            ],
            contribution_starting_earlier: [
                CalculationPart(explanation="earlier 1", value=Decimal(2)),
                CalculationPart(explanation="earlier 2", value=Decimal(3)),
            ],
        }
        mock_get_calculation_parts_for_single_contribution_within_range.side_effect = (
            lambda contribution, **_: parts_by_contribution[contribution]
        )
        range_start = datetime.date(year=1990, month=1, day=1)
        range_end = datetime.date(year=1990, month=12, day=31)

        result = MonthPaymentBuilderSolidarityContributions.get_calculation_parts(
            range_start=range_start,
            range_end=range_end,
            contracts=[
                contribution_starting_later,
                contribution_inactive,
                contribution_starting_earlier,
            ],
            cache={},
        )

        self.assertEqual(
            ["earlier 1", "earlier 2", "later"],
            [part.explanation for part in result],
        )
        self.assertEqual(
            2,
            mock_get_calculation_parts_for_single_contribution_within_range.call_count,
        )
        mock_get_calculation_parts_for_single_contribution_within_range.assert_has_calls(
            [
                call(
                    contribution=contribution,
                    range_start=range_start,
                    range_end=range_end,
                )
                for contribution in [
                    contribution_starting_earlier,
                    contribution_starting_later,
                ]
            ]
        )
