import datetime
from decimal import Decimal

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory


class TestGetAmountForSingleContributionWithinRange(SimpleTestCase):
    def test_getAmountForSingleContributionWithinRange_contributionIsNotWithinRange_returnsDecimalZero(
        self,
    ):
        contribution = SolidarityContributionFactory.build(
            amount=Decimal(100), start_date=datetime.date(year=1992, month=4, day=1)
        )

        result = MonthPaymentBuilderSolidarityContributions.get_amount_for_single_contribution_within_range(
            range_start=datetime.date(year=1992, month=1, day=1),
            range_end=datetime.date(year=1992, month=3, day=31),
            contribution=contribution,
        )

        self.assertEqual(Decimal(0), result)

    def test_getAmountForSingleContributionWithinRange_default_returnsCorrectValue(
        self,
    ):
        contribution = SolidarityContributionFactory.build(
            amount=Decimal(100), start_date=datetime.date(year=1993, month=2, day=15)
        )

        result = MonthPaymentBuilderSolidarityContributions.get_amount_for_single_contribution_within_range(
            range_start=datetime.date(year=1993, month=1, day=1),
            range_end=datetime.date(year=1993, month=3, day=31),
            contribution=contribution,
        )

        self.assertEqual(
            Decimal("150"), result
        )  # should be 100 for march (full month) and 50 for february (half month)
