import datetime
from decimal import Decimal
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory


class TestGetTotalToPay(SimpleTestCase):
    def test_getTotalToPay_noContributions_returnsZero(self):
        result = MonthPaymentBuilderSolidarityContributions.get_total_to_pay(
            range_start=datetime.date(year=1990, month=1, day=1),
            range_end=datetime.date(year=1991, month=1, day=1),
            contracts=[],
            cache={},
        )

        self.assertEqual(Decimal(0), result)

    @patch.object(
        MonthPaymentBuilderSolidarityContributions,
        "get_amount_for_single_contribution_within_range",
        autospec=True,
    )
    def test_getTotalToPay_default_returnsSumOfOnlyActiveContributions(
        self, mock_get_amount_for_single_contribution_within_range: Mock
    ):
        contribution_active_1 = SolidarityContributionFactory.build(
            start_date=datetime.date(year=1990, month=2, day=1)
        )
        contribution_active_2 = SolidarityContributionFactory.build(
            start_date=datetime.date(year=1990, month=2, day=1)
        )
        contribution_inactive = SolidarityContributionFactory.build(
            start_date=datetime.date(year=1989, month=1, day=1)
        )

        amounts = {
            contribution_active_1: Decimal("15"),
            contribution_active_2: Decimal("7.8"),
        }
        mock_get_amount_for_single_contribution_within_range.side_effect = (
            lambda contribution, range_start, range_end: amounts[contribution]
        )
        range_start = datetime.date(year=1990, month=1, day=1)
        range_end = datetime.date(year=1991, month=1, day=1)

        result = MonthPaymentBuilderSolidarityContributions.get_total_to_pay(
            range_start=range_start,
            range_end=range_end,
            contracts=[
                contribution_active_1,
                contribution_active_2,
                contribution_inactive,
            ],
            cache={},
        )

        self.assertEqual(Decimal("22.8"), result)

        self.assertEqual(
            2, mock_get_amount_for_single_contribution_within_range.call_count
        )
        mock_get_amount_for_single_contribution_within_range.assert_has_calls(
            [
                call(
                    contribution=contribution,
                    range_start=range_start,
                    range_end=range_end,
                )
                for contribution in [contribution_active_1, contribution_active_2]
            ],
            any_order=True,
        )
