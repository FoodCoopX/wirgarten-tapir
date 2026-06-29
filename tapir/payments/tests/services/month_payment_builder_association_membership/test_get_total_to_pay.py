import datetime
from decimal import Decimal
from unittest.mock import patch, Mock, call

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetTotalToPay(TapirUnitTest):
    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "get_amount_for_single_membership_within_range",
        autospec=True,
    )
    def test_getTotalToPay_default_returnsSumOfMembershipCostsWithinRange(
        self, mock_get_amount_for_single_membership_within_range: Mock
    ):
        membership_within_range_1 = AssociationMembershipFactory.build(
            start_date=datetime.date(year=1988, month=1, day=1), end_date=None
        )
        membership_within_range_2 = AssociationMembershipFactory.build(
            start_date=datetime.date(year=1990, month=6, day=15),
            end_date=datetime.date(year=1990, month=12, day=1),
        )
        membership_outside_of_range = AssociationMembershipFactory.build(
            start_date=datetime.date(year=1989, month=6, day=15),
            end_date=datetime.date(year=1989, month=12, day=1),
        )

        amounts_to_pay = {
            membership_within_range_1: Decimal(10),
            membership_within_range_2: Decimal(15),
        }
        mock_get_amount_for_single_membership_within_range.side_effect = (
            lambda membership, **kwargs: amounts_to_pay[membership]
        )

        cache = Mock()
        range_start = datetime.date(year=1990, month=1, day=1)
        range_end = datetime.date(year=1990, month=12, day=31)

        result = MonthPaymentBuilderAssociationMembership.get_total_to_pay(
            range_start=range_start,
            range_end=range_end,
            contracts=[
                membership_within_range_1,
                membership_within_range_2,
                membership_outside_of_range,
            ],
            cache=cache,
        )

        self.assertEqual(Decimal(25), result)

        self.assertEqual(
            2, mock_get_amount_for_single_membership_within_range.call_count
        )
        mock_get_amount_for_single_membership_within_range.assert_has_calls(
            [
                call(
                    membership=membership,
                    range_start=range_start,
                    range_end=range_end,
                    cache=cache,
                )
                for membership in [
                    membership_within_range_1,
                    membership_within_range_2,
                ]
            ],
            any_order=True,
        )

    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "get_amount_for_single_membership_within_range",
        autospec=True,
    )
    def test_getTotalToPay_noMembershipWithinRange_returnsZero(
        self, mock_get_amount_for_single_membership_within_range: Mock
    ):
        membership_outside_of_range = AssociationMembershipFactory.build(
            start_date=datetime.date(year=1989, month=6, day=15),
            end_date=datetime.date(year=1989, month=12, day=1),
        )

        cache = Mock()
        range_start = datetime.date(year=1990, month=1, day=1)
        range_end = datetime.date(year=1990, month=12, day=31)

        result = MonthPaymentBuilderAssociationMembership.get_total_to_pay(
            range_start=range_start,
            range_end=range_end,
            contracts=[membership_outside_of_range],
            cache=cache,
        )

        self.assertEqual(Decimal(0), result)
        mock_get_amount_for_single_membership_within_range.assert_not_called()
