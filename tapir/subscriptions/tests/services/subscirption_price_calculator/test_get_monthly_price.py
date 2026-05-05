from decimal import Decimal
from unittest.mock import Mock, patch

from django.core.exceptions import ImproperlyConfigured

from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.tests.factories import SubscriptionFactory, ProductPriceFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetMonthlyPrice(TapirUnitTest):
    @patch(
        "tapir.subscriptions.services.subscription_price_calculator.get_product_price",
        autospec=True,
    )
    def test_getMonthlyPrice_priceIsOverridden_returnsOverride(
        self, mock_get_product_price: Mock
    ):
        subscription = SubscriptionFactory.build(price_override=Decimal("12.75"))

        result = SubscriptionPriceCalculator.get_monthly_price(
            subscription=subscription, reference_date=Mock(), cache=Mock()
        )

        self.assertEqual(Decimal("12.75"), result)

        mock_get_product_price.assert_not_called()

    @patch(
        "tapir.subscriptions.services.subscription_price_calculator.get_product_price",
        autospec=True,
    )
    def test_getMonthlyPrice_overrideIsZero_returnsZero(
        self, mock_get_product_price: Mock
    ):
        # making sure that 0 is not perceived as "no override"
        subscription = SubscriptionFactory.build(price_override=Decimal("0"))

        result = SubscriptionPriceCalculator.get_monthly_price(
            subscription=subscription, reference_date=Mock(), cache=Mock()
        )

        self.assertEqual(Decimal("0"), result)

        mock_get_product_price.assert_not_called()

    @patch(
        "tapir.subscriptions.services.subscription_price_calculator.get_product_price",
        autospec=True,
    )
    def test_getMonthlyPrice_noPriceFound_raisesError(
        self, mock_get_product_price: Mock
    ):
        reference_date = Mock()
        cache = Mock()
        subscription = SubscriptionFactory.build()
        mock_get_product_price.return_value = None

        with self.assertRaises(ImproperlyConfigured):
            SubscriptionPriceCalculator.get_monthly_price(
                subscription=subscription, reference_date=reference_date, cache=cache
            )

        mock_get_product_price.assert_called_once_with(
            product=subscription.product, reference_date=reference_date, cache=cache
        )

    @patch(
        "tapir.subscriptions.services.subscription_price_calculator.get_product_price",
        autospec=True,
    )
    def test_getMonthlyPrice_default_returnsPriceMultipliedByQuantity(
        self, mock_get_product_price: Mock
    ):
        reference_date = Mock()
        cache = Mock()
        subscription = SubscriptionFactory.build(quantity=5)
        mock_get_product_price.return_value = ProductPriceFactory.build(
            price=Decimal("12.5")
        )

        result = SubscriptionPriceCalculator.get_monthly_price(
            subscription=subscription, reference_date=reference_date, cache=cache
        )

        self.assertEqual(Decimal("62.5"), result)
        mock_get_product_price.assert_called_once_with(
            product=subscription.product, reference_date=reference_date, cache=cache
        )
