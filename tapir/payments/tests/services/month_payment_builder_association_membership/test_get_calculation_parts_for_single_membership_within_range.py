import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, call

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.utils.dataclasses import CalculationPart
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetCalculationPartsForSingleMembershipWithinRange(TapirUnitTest):
    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "is_membership_fee_waived",
        return_value=False,
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "_build_calculation_part_for_membership_within_month",
        autospec=True,
    )
    def test_getCalculationPartsForSingleMembershipWithinRange_default_returnsPartOfEachCoveredMonth(
        self,
        mock_build_calculation_part_for_membership_within_month: MagicMock,
        mock_is_membership_fee_waived: MagicMock,
    ):
        membership = AssociationMembershipFactory.build()
        cache = {}
        parts_by_month = {
            2: None,
            3: CalculationPart(explanation="March", value=Decimal(10)),
            4: CalculationPart(explanation="April", value=Decimal(10)),
            5: CalculationPart(explanation="May", value=Decimal(15)),
        }
        mock_build_calculation_part_for_membership_within_month.side_effect = (
            lambda first_of_month, **_: parts_by_month[first_of_month.month]
        )

        result = MonthPaymentBuilderAssociationMembership._get_calculation_parts_for_single_membership_within_range(
            range_start=datetime.date(year=2012, month=2, day=1),
            range_end=datetime.date(year=2012, month=5, day=31),
            membership=membership,
            cache=cache,
        )

        self.assertEqual(
            [parts_by_month[3], parts_by_month[4], parts_by_month[5]], result
        )
        mock_build_calculation_part_for_membership_within_month.assert_has_calls(
            [
                call(
                    first_of_month=datetime.date(year=2012, month=month, day=1),
                    membership=membership,
                    cache=cache,
                )
                for month in parts_by_month.keys()
            ]
        )
        self.assertEqual(
            4, mock_build_calculation_part_for_membership_within_month.call_count
        )
        mock_is_membership_fee_waived.assert_called_once_with(
            member=membership.member,
            range_start=datetime.date(year=2012, month=2, day=1),
            range_end=datetime.date(year=2012, month=5, day=31),
            cache=cache,
        )

    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "is_membership_fee_waived",
        return_value=True,
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "_build_calculation_part_for_membership_within_month",
        autospec=True,
    )
    def test_getCalculationPartsForSingleMembershipWithinRange_membershipFeeWaived_returnsEmptyList(
        self,
        mock_build_calculation_part_for_membership_within_month: MagicMock,
        mock_is_membership_fee_waived: MagicMock,
    ):
        membership = AssociationMembershipFactory.build()
        cache = {}
        range_start = datetime.date(year=2012, month=2, day=1)
        range_end = datetime.date(year=2012, month=5, day=31)

        result = MonthPaymentBuilderAssociationMembership._get_calculation_parts_for_single_membership_within_range(
            range_start=range_start,
            range_end=range_end,
            membership=membership,
            cache=cache,
        )

        self.assertEqual([], result)
        mock_is_membership_fee_waived.assert_called_once_with(
            member=membership.member,
            range_start=range_start,
            range_end=range_end,
            cache=cache,
        )
        mock_build_calculation_part_for_membership_within_month.assert_not_called()
