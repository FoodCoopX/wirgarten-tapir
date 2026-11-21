import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, call

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.utils.dataclasses import CalculationPart
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetCalculationParts(TapirUnitTest):
    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "_get_calculation_parts_for_single_membership_within_range",
        autospec=True,
    )
    def test_getCalculationParts_default_returnsPartsOfActiveMembershipsSortedByStartDate(
        self, mock_get_calculation_parts_for_single_membership_within_range: MagicMock
    ):
        membership_starting_later = AssociationMembershipFactory.build(
            start_date=datetime.date(year=1990, month=6, day=15),
            end_date=datetime.date(year=1990, month=12, day=1),
        )
        membership_starting_earlier = AssociationMembershipFactory.build(
            start_date=datetime.date(year=1988, month=1, day=1), end_date=None
        )
        membership_inactive = AssociationMembershipFactory.build(
            start_date=datetime.date(year=1989, month=6, day=15),
            end_date=datetime.date(year=1989, month=12, day=1),
        )
        parts_by_membership = {
            membership_starting_later: [
                CalculationPart(explanation="later", value=Decimal(1))
            ],
            membership_starting_earlier: [
                CalculationPart(explanation="earlier 1", value=Decimal(2)),
                CalculationPart(explanation="earlier 2", value=Decimal(3)),
            ],
        }
        mock_get_calculation_parts_for_single_membership_within_range.side_effect = (
            lambda membership, **_: parts_by_membership[membership]
        )
        range_start = datetime.date(year=1990, month=1, day=1)
        range_end = datetime.date(year=1990, month=12, day=31)
        cache = {}

        result = MonthPaymentBuilderAssociationMembership.get_calculation_parts(
            range_start=range_start,
            range_end=range_end,
            contracts=[
                membership_starting_later,
                membership_inactive,
                membership_starting_earlier,
            ],
            cache=cache,
        )

        self.assertEqual(
            ["earlier 1", "earlier 2", "later"],
            [part.explanation for part in result],
        )
        self.assertEqual(
            2,
            mock_get_calculation_parts_for_single_membership_within_range.call_count,
        )
        mock_get_calculation_parts_for_single_membership_within_range.assert_has_calls(
            [
                call(
                    membership=membership,
                    range_start=range_start,
                    range_end=range_end,
                    cache=cache,
                )
                for membership in [
                    membership_starting_earlier,
                    membership_starting_later,
                ]
            ]
        )
