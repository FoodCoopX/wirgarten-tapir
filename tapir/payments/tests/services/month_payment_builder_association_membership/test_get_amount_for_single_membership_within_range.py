import datetime
from decimal import Decimal
from unittest.mock import patch, Mock, call

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetAmountForSingleMembershipWithinRange(TapirUnitTest):
    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "get_amount_to_pay_for_membership_within_month",
        autospec=True,
    )
    def test_default_returnsSumOfMonthlyAmounts(
        self, mock_get_amount_to_pay_for_membership_within_month: Mock
    ):
        membership = AssociationMembershipFactory.build()
        cache = Mock()
        amounts_per_month = {
            2: Decimal(0),
            3: Decimal(10),
            4: Decimal(10),
            5: Decimal(15),
        }
        mock_get_amount_to_pay_for_membership_within_month.side_effect = (
            lambda first_of_month, **kwargs: amounts_per_month[first_of_month.month]
        )

        result = MonthPaymentBuilderAssociationMembership.get_amount_for_single_membership_within_range(
            range_start=datetime.date(year=2012, month=2, day=1),
            range_end=datetime.date(year=2012, month=5, day=30),
            membership=membership,
            cache=cache,
        )

        self.assertEqual(Decimal(35), result)

        self.assertEqual(
            4, mock_get_amount_to_pay_for_membership_within_month.call_count
        )
        mock_get_amount_to_pay_for_membership_within_month.assert_has_calls(
            [
                call(
                    first_of_month=datetime.date(year=2012, month=month, day=1),
                    membership=membership,
                    cache=cache,
                )
                for month in amounts_per_month.keys()
            ],
            any_order=True,
        )
