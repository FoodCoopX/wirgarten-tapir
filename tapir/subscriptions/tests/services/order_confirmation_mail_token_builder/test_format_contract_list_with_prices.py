import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.subscriptions.services.order_confirmation_mail_token_builder import (
    OrderConfirmationMailTokenBuilder,
)
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestFormatContractListWithPrices(TapirUnitTest):
    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.SubscriptionPriceCalculator.get_monthly_price",
        autospec=True,
    )
    def test_formatContractListWithPrices_default_includesMonthlyPricePerContract(
        self, mock_get_monthly_price: Mock
    ):
        reference_date = datetime.date(year=2026, month=5, day=11)
        cache = {}
        subscription = SubscriptionFactory.build(
            quantity=2,
            product__name="M",
            product__type__name="Basket",
            product__id="product-b",
            start_date=datetime.date(year=2026, month=5, day=11),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        mock_get_monthly_price.return_value = Decimal("21.50")

        result = OrderConfirmationMailTokenBuilder.format_contract_list_with_prices(
            subscriptions=[subscription],
            reference_date=reference_date,
            cache=cache,
        )

        self.assertEqual(
            "<ul><li>2 × M Basket  (11.05.2026 - 31.12.2026) — 21,50 € / Monat</li></ul>",
            result,
        )
        mock_get_monthly_price.assert_called_once_with(
            subscription=subscription,
            reference_date=reference_date,
            cache=cache,
        )

    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.SubscriptionPriceCalculator.get_monthly_price",
        autospec=True,
    )
    def test_formatContractListWithPrices_noPriceFound_omitsPriceSuffix(
        self, mock_get_monthly_price: Mock
    ):
        reference_date = datetime.date(year=2026, month=5, day=11)
        subscription = SubscriptionFactory.build(
            quantity=1,
            product__name="M",
            product__type__name="Basket",
            start_date=datetime.date(year=2026, month=5, day=11),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        mock_get_monthly_price.side_effect = TapirImproperlyConfigured("no price")

        result = OrderConfirmationMailTokenBuilder.format_contract_list_with_prices(
            subscriptions=[subscription],
            reference_date=reference_date,
            cache={},
        )

        self.assertEqual(
            "<ul><li>1 × M Basket  (11.05.2026 - 31.12.2026)</li></ul>",
            result,
        )

    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.SubscriptionPriceCalculator.get_monthly_price",
        autospec=True,
    )
    def test_formatContractListWithPrices_severalSubscriptions_sortsByProductId(
        self, mock_get_monthly_price: Mock
    ):
        reference_date = datetime.date(year=2026, month=1, day=1)
        cache = {}
        subscription_later = SubscriptionFactory.build(
            quantity=1,
            product__name="B",
            product__type__name="Herb",
            product__id="product-z",
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        subscription_earlier = SubscriptionFactory.build(
            quantity=3,
            product__name="A",
            product__type__name="Veg",
            product__id="product-a",
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        mock_get_monthly_price.side_effect = [Decimal("10"), Decimal("5")]

        result = OrderConfirmationMailTokenBuilder.format_contract_list_with_prices(
            subscriptions=[subscription_later, subscription_earlier],
            reference_date=reference_date,
            cache=cache,
        )

        self.assertEqual(
            "<ul><li>3 × A Veg  (01.01.2026 - 31.12.2026) — 10,00 € / Monat</li>"
            "<li>1 × B Herb  (01.01.2026 - 31.12.2026) — 5,00 € / Monat</li></ul>",
            result,
        )
