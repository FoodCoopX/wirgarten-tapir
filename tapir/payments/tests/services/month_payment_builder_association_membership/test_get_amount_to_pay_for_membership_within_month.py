import datetime
from decimal import Decimal
from unittest.mock import patch, Mock

from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetAmountToPayForMembershipWithinMonth(TapirUnitTest):
    @patch.object(AssociationMembershipTypePriceGetter, "get_price", autospec=True)
    def test_getAmountToPayForMembershipWithinMonth_monthFullyCovered_returnsFullPrice(
        self, mock_get_price: Mock
    ):
        mock_get_price.return_value = Decimal(10)
        cache = Mock()
        membership = AssociationMembershipFactory.build(
            start_date=datetime.date(year=2013, month=1, day=1)
        )

        result = MonthPaymentBuilderAssociationMembership.get_amount_to_pay_for_membership_within_month(
            first_of_month=datetime.date(year=2013, month=4, day=1),
            membership=membership,
            cache=cache,
        )

        self.assertEqual(Decimal(10), result)
        mock_get_price.assert_called_once_with(
            membership_type=membership.type,
            reference_date=datetime.date(year=2013, month=4, day=1),
            cache=cache,
        )

    @patch.object(AssociationMembershipTypePriceGetter, "get_price", autospec=True)
    def test_getAmountToPayForMembershipWithinMonth_monthPartiallyCovered_returnsPartialPrice(
        self, mock_get_price: Mock
    ):
        mock_get_price.return_value = Decimal(10)
        cache = Mock()
        membership = AssociationMembershipFactory.build(
            start_date=datetime.date(year=2013, month=1, day=1),
            end_date=datetime.date(year=2013, month=4, day=18),
        )

        result = MonthPaymentBuilderAssociationMembership.get_amount_to_pay_for_membership_within_month(
            first_of_month=datetime.date(year=2013, month=4, day=1),
            membership=membership,
            cache=cache,
        )

        self.assertEqual(Decimal("6.00"), result)  # 18 days is 60% of the month
        mock_get_price.assert_called_once_with(
            membership_type=membership.type,
            reference_date=datetime.date(year=2013, month=4, day=1),
            cache=cache,
        )
