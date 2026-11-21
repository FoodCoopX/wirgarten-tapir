from decimal import Decimal

from tapir.subscriptions.services.admin_subscription_change_member_data_builder import (
    AdminSubscriptionChangeMemberDataBuilder,
)
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAdminSubscriptionChangeMemberDataBuilderGetPriceCategory(TapirUnitTest):
    def test_getPriceCategory_noOverride_returnsStandard(self):
        self.assertEqual(
            AdminSubscriptionChangeMemberDataBuilder.PRICE_STANDARD,
            AdminSubscriptionChangeMemberDataBuilder.get_price_category(
                SubscriptionFactory.build(price_override=None)
            ),
        )

    def test_getPriceCategory_overrideZero_returnsExempt(self):
        self.assertEqual(
            AdminSubscriptionChangeMemberDataBuilder.PRICE_EXEMPT,
            AdminSubscriptionChangeMemberDataBuilder.get_price_category(
                SubscriptionFactory.build(price_override=Decimal(0))
            ),
        )

    def test_getPriceCategory_otherOverride_returnsPersonalised(self):
        self.assertEqual(
            AdminSubscriptionChangeMemberDataBuilder.PRICE_PERSONALISED,
            AdminSubscriptionChangeMemberDataBuilder.get_price_category(
                SubscriptionFactory.build(price_override=Decimal("12.50"))
            ),
        )
