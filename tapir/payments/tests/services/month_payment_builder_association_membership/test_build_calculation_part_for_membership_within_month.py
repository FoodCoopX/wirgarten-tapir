import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.utils.dataclasses import CalculationPart
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    AssociationMembershipTypePriceGetter,
    "get_price",
    autospec=True,
    return_value=Decimal(10),
)
class TestBuildCalculationPartForMembershipWithinMonth(TapirUnitTest):
    FIRST_OF_APRIL = datetime.date(year=2013, month=4, day=1)

    @staticmethod
    def _build_membership(end_date: datetime.date | None) -> AssociationMembership:
        return AssociationMembershipFactory.build(
            type__name="Fördermitglied",
            start_date=datetime.date(year=2013, month=1, day=1),
            end_date=end_date,
        )

    @classmethod
    def _build_part(
        cls, membership: AssociationMembership, cache: dict | None = None
    ) -> CalculationPart | None:
        return MonthPaymentBuilderAssociationMembership._build_calculation_part_for_membership_within_month(
            first_of_month=cls.FIRST_OF_APRIL,
            membership=membership,
            cache={} if cache is None else cache,
        )

    def test_buildCalculationPartForMembershipWithinMonth_monthFullyCovered_returnsFullPrice(
        self, mock_get_price: MagicMock
    ):
        membership = self._build_membership(end_date=None)
        cache = {}

        result = self._build_part(membership=membership, cache=cache)

        self.assertEqual(
            CalculationPart(
                explanation="April 2013, Vereinsmitgliedschaft Fördermitglied: 10,00 € monatlich (voller Monat)",
                value=Decimal(10),
            ),
            result,
        )
        mock_get_price.assert_called_once_with(
            membership_type=membership.type,
            reference_date=self.FIRST_OF_APRIL,
            cache=cache,
        )

    def test_buildCalculationPartForMembershipWithinMonth_monthPartiallyCovered_returnsShareByDays(
        self, _: MagicMock
    ):
        result = self._build_part(
            membership=self._build_membership(
                end_date=datetime.date(year=2013, month=4, day=18)
            )
        )

        self.assertEqual(
            CalculationPart(
                explanation="April 2013, Vereinsmitgliedschaft Fördermitglied: 10,00 € × 18 von 30 Tagen = 6,00 €",
                value=Decimal("6.00"),
            ),
            result,
        )

    def test_buildCalculationPartForMembershipWithinMonth_monthNotCovered_returnsNone(
        self, mock_get_price: MagicMock
    ):
        result = self._build_part(
            membership=self._build_membership(
                end_date=datetime.date(year=2013, month=3, day=31)
            )
        )

        self.assertIsNone(result)
        mock_get_price.assert_not_called()
