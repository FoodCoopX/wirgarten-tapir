import datetime
from decimal import Decimal
from unittest.mock import patch, Mock

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.constants import WEEKLY, ODD_WEEKS
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    MemberSolidarityContributionService, "get_member_contribution", autospec=True
)
class TestGetSolidarityContributionPart(TapirUnitTest):
    # 2021 has 52 weeks
    JOKER_DATE = datetime.date(year=2021, month=5, day=7)

    def build_subscription(self, delivery_cycle: str):
        product_type = ProductTypeFactory.build(delivery_cycle=delivery_cycle)
        return SubscriptionFactory.build(product__type=product_type)

    def build_cache(self, product_type_id: str):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.JOKERS_SOLIDARITY_CONTRIBUTION_PRODUCT_TYPE,
            value=product_type_id,
        )
        return cache

    def get_part(self, subscriptions: list, cache: dict, member=None):
        return JokerValueService._get_solidarity_contribution_part(
            member=member or MemberFactory.build(),
            joker_date=self.JOKER_DATE,
            subscriptions=subscriptions,
            cache=cache,
        )

    def test_getSolidarityContributionPart_selectedTypeDelivered_returnsPart(
        self, mock_get_member_contribution: Mock
    ):
        mock_get_member_contribution.return_value = Decimal(20)
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0])
        other_subscription = self.build_subscription(delivery_cycle=WEEKLY[0])
        cache = self.build_cache(product_type_id=subscription.product.type.id)
        member = MemberFactory.build()

        part = self.get_part(
            subscriptions=[other_subscription, subscription],
            cache=cache,
            member=member,
        )

        self.assertAlmostEqual(Decimal("4.62"), part.value, places=2)
        self.assertEqual(
            "Solidarbeitrag: 20,00 € monatlich × 12 ÷ 52 Wochen = 4,62 €",
            part.explanation,
        )
        mock_get_member_contribution.assert_called_once_with(
            member_id=member.id, reference_date=self.JOKER_DATE, cache=cache
        )

    def test_getSolidarityContributionPart_selectedTypeDeliveredEveryTwoWeeks_valueDoubled(
        self, mock_get_member_contribution: Mock
    ):
        mock_get_member_contribution.return_value = Decimal(-5)
        subscription = self.build_subscription(delivery_cycle=ODD_WEEKS[0])

        part = self.get_part(
            subscriptions=[subscription],
            cache=self.build_cache(product_type_id=subscription.product.type.id),
        )

        self.assertAlmostEqual(Decimal("-2.31"), part.value, places=2)
        self.assertEqual(
            "Solidarbeitrag: -5,00 € monatlich × 12 ÷ 52 Wochen × 2 (Lieferung alle 2 Wochen) = -2,31 €",
            part.explanation,
        )

    def test_getSolidarityContributionPart_selectedTypeNotInSubscriptions_returnsNone(
        self, mock_get_member_contribution: Mock
    ):
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0])

        part = self.get_part(
            subscriptions=[subscription],
            cache=self.build_cache(product_type_id="other_product_type_id"),
        )

        self.assertIsNone(part)
        mock_get_member_contribution.assert_not_called()

    def test_getSolidarityContributionPart_contributionIsZero_returnsNone(
        self, mock_get_member_contribution: Mock
    ):
        mock_get_member_contribution.return_value = Decimal(0)
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0])

        part = self.get_part(
            subscriptions=[subscription],
            cache=self.build_cache(product_type_id=subscription.product.type.id),
        )

        self.assertIsNone(part)
