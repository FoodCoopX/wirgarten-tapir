import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_size_change_order_builder import (
    AdminSizeChangeOrderBuilder,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Product, Subscription
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
class TestAdminSizeChangeOrderBuilderBuildOrder(TapirUnitTest):
    CHANGE_DATE = datetime.date(year=2027, month=6, day=7)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.build()
        self.growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        product_type = ProductTypeFactory.build()
        self.product_small = ProductFactory.build(type=product_type)
        self.product_medium = ProductFactory.build(type=product_type)
        self.product_large = ProductFactory.build(type=product_type)

    def _build_subscription(self, product: Product, quantity: int) -> Subscription:
        return SubscriptionFactory.build(
            member=self.member,
            period=self.growing_period,
            product=product,
            quantity=quantity,
        )

    def test_buildOrder_quantityOne_replacesOldProductByNewProduct(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        subscription = self._build_subscription(product=self.product_small, quantity=1)
        mock_get_all_subscriptions_for_member.return_value = [subscription]
        cache = {}

        order = AdminSizeChangeOrderBuilder.build_order(
            member=self.member,
            subscription=subscription,
            new_product=self.product_medium,
            change_date=self.CHANGE_DATE,
            cache=cache,
        )

        self.assertEqual({self.product_medium: 1}, order)
        mock_get_all_subscriptions_for_member.assert_called_once_with(
            member_id=self.member.id, cache=cache
        )

    def test_buildOrder_quantityThree_keepsOldProductWithQuantityTwo(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        subscription = self._build_subscription(product=self.product_small, quantity=3)
        mock_get_all_subscriptions_for_member.return_value = [subscription]

        order = AdminSizeChangeOrderBuilder.build_order(
            member=self.member,
            subscription=subscription,
            new_product=self.product_medium,
            change_date=self.CHANGE_DATE,
            cache={},
        )

        self.assertEqual({self.product_small: 2, self.product_medium: 1}, order)

    def test_buildOrder_newProductAlreadySubscribed_addsToExistingQuantity(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        subscription = self._build_subscription(product=self.product_small, quantity=1)
        mock_get_all_subscriptions_for_member.return_value = [
            subscription,
            self._build_subscription(product=self.product_medium, quantity=1),
            self._build_subscription(product=self.product_large, quantity=2),
        ]

        order = AdminSizeChangeOrderBuilder.build_order(
            member=self.member,
            subscription=subscription,
            new_product=self.product_medium,
            change_date=self.CHANGE_DATE,
            cache={},
        )

        self.assertEqual({self.product_medium: 2, self.product_large: 2}, order)

    def test_buildOrder_otherTypesAndInactiveSubscriptionsExists_otherTypesAreIgnored(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        subscription = self._build_subscription(product=self.product_small, quantity=1)
        ended_subscription = self._build_subscription(
            product=self.product_large, quantity=1
        )
        ended_subscription.end_date = self.CHANGE_DATE - datetime.timedelta(days=1)
        future_subscription = self._build_subscription(
            product=self.product_large, quantity=1
        )
        future_subscription.start_date = self.CHANGE_DATE + datetime.timedelta(days=7)
        other_type_subscription = self._build_subscription(
            product=ProductFactory.build(), quantity=1
        )
        mock_get_all_subscriptions_for_member.return_value = [
            subscription,
            ended_subscription,
            future_subscription,
            other_type_subscription,
        ]

        order = AdminSizeChangeOrderBuilder.build_order(
            member=self.member,
            subscription=subscription,
            new_product=self.product_medium,
            change_date=self.CHANGE_DATE,
            cache={},
        )

        self.assertEqual({self.product_medium: 1}, order)

    def test_buildOrder_changeFromNextPeriod_usesSubscriptionsOfLastDayOfPreviousSubscription(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        subscription = self._build_subscription(product=self.product_small, quantity=1)
        other_subscription = self._build_subscription(
            product=self.product_large, quantity=1
        )
        mock_get_all_subscriptions_for_member.return_value = [
            subscription,
            other_subscription,
        ]

        order = AdminSizeChangeOrderBuilder.build_order(
            member=self.member,
            subscription=subscription,
            new_product=self.product_medium,
            change_date=datetime.date(year=2028, month=1, day=1),
            cache={},
        )

        self.assertEqual({self.product_large: 1, self.product_medium: 1}, order)
