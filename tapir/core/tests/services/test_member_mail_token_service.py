import datetime
from unittest.mock import MagicMock, Mock, patch

from tapir_mail.models import StaticSegmentRecipient

from tapir.core.services import member_mail_token_service
from tapir.core.services.member_mail_token_service import MemberMailTokenService
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Product, Subscription
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductFactory,
    ProductPriceFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestMemberMailTokenService(TapirUnitTest):
    def test_getPostAddress_default_returnsCorrectString(self):
        member = MemberFactory.build(
            street="aaa", street_2="bbb", postcode="12345", city="ccc"
        )

        result = MemberMailTokenService.get_post_address(recipient=member, cache=Mock())

        self.assertEqual("aaa, bbb, 12345 ccc", result)

    def test_getPostAddress_recipientIsStaticRecipient_returnsEmptyString(self):
        recipient = StaticSegmentRecipient()

        result = MemberMailTokenService.get_post_address(
            recipient=recipient, cache=Mock()
        )

        self.assertEqual("", result)

    TODAY = datetime.date(year=2026, month=5, day=10)

    @staticmethod
    def _build_subscription(
        product: Product,
        quantity: int,
        start_date: datetime.date = datetime.date(year=2026, month=1, day=1),
        end_date: datetime.date = datetime.date(year=2026, month=12, day=31),
    ) -> Subscription:
        return SubscriptionFactory.build(
            product=product,
            quantity=quantity,
            start_date=start_date,
            end_date=end_date,
        )

    @staticmethod
    def _build_product(name: str, must_be_subscribed_to: bool = True) -> Product:
        return ProductFactory.build(
            name=name,
            type=ProductTypeFactory.build(
                name="Ernteanteile", must_be_subscribed_to=must_be_subscribed_to
            ),
        )

    def test_getBaseSubscriptionsText_recipientIsStaticRecipient_returnsEmptyString(
        self,
    ):
        result = MemberMailTokenService.get_base_subscriptions_text(
            recipient=StaticSegmentRecipient(), cache={}
        )

        self.assertEqual("", result)

    @patch.object(member_mail_token_service, "get_today", autospec=True)
    @patch.object(member_mail_token_service, "get_product_price", autospec=True)
    @patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
    def test_getBaseSubscriptionsText_default_listsActiveBaseProductsSortedByPrice(
        self,
        mock_get_all_subscriptions_for_member: MagicMock,
        mock_get_product_price: MagicMock,
        mock_get_today: MagicMock,
    ):
        mock_get_today.return_value = self.TODAY
        product_m = self._build_product(name="M")
        product_s = self._build_product(name="S")
        product_l = self._build_product(name="L")
        additional_product = self._build_product(
            name="Eier", must_be_subscribed_to=False
        )
        prices = {product_s: 10, product_m: 20, product_l: 30}
        mock_get_product_price.side_effect = (
            lambda product, reference_date, cache: ProductPriceFactory.build(
                price=prices[product]
            )
        )
        mock_get_all_subscriptions_for_member.return_value = [
            self._build_subscription(product=product_m, quantity=1),
            self._build_subscription(product=product_m, quantity=1),
            self._build_subscription(product=product_s, quantity=1),
            self._build_subscription(product=additional_product, quantity=1),
            self._build_subscription(
                product=product_l,
                quantity=1,
                end_date=datetime.date(year=2026, month=5, day=9),
            ),
            self._build_subscription(
                product=product_l,
                quantity=1,
                start_date=datetime.date(year=2026, month=5, day=11),
            ),
        ]
        member = MemberFactory.build()
        cache = {}

        result = MemberMailTokenService.get_base_subscriptions_text(
            recipient=member, cache=cache
        )

        self.assertEqual("einen S-Ernteanteil + 2 M-Ernteanteile", result)
        mock_get_all_subscriptions_for_member.assert_called_once_with(
            member_id=member.id, cache=cache
        )
        mock_get_today.assert_called_once_with(cache=cache)

    @patch.object(member_mail_token_service, "get_today", autospec=True)
    @patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
    def test_getBaseSubscriptionsText_noActiveSubscription_returnsEmptyString(
        self,
        mock_get_all_subscriptions_for_member: MagicMock,
        mock_get_today: MagicMock,
    ):
        mock_get_today.return_value = self.TODAY
        mock_get_all_subscriptions_for_member.return_value = []

        result = MemberMailTokenService.get_base_subscriptions_text(
            recipient=MemberFactory.build(), cache={}
        )

        self.assertEqual("", result)
