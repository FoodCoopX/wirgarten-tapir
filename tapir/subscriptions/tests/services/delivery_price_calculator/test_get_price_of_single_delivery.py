import datetime
from decimal import Decimal
from unittest.mock import patch, Mock

from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetPriceOfSingleDelivery(TapirUnitTest):
    @patch.object(
        DeliveryPriceCalculator, "get_number_of_months_in_growing_period", autospec=True
    )
    @patch(
        "tapir.subscriptions.services.delivery_price_calculator.get_product_price",
        autospec=True,
    )
    def test_getPriceOfSingleDelivery_default_returnsCorrectPrice(
        self,
        mock_get_product_price: Mock,
        mock_get_number_of_months_in_growing_period: Mock,
    ):
        subscription, product = self.setup_mocks(mock_get_product_price)
        date = datetime.date(year=2021, month=5, day=7)  # 2021 has 52 weeks

        result = DeliveryPriceCalculator.get_price_of_single_delivery_for_subscription(
            subscription, date, cache={}
        )

        self.assert_correct(
            result=result,
            product=product,
            date=date,
            nb_weeks=52,
            mock_get_product_price=mock_get_product_price,
            mock_get_number_of_months_in_growing_period=mock_get_number_of_months_in_growing_period,
        )

    @patch.object(
        DeliveryPriceCalculator, "get_number_of_months_in_growing_period", autospec=True
    )
    @patch(
        "tapir.subscriptions.services.delivery_price_calculator.get_product_price",
        autospec=True,
    )
    def test_getPriceOfSingleDelivery_yearWith53Weeks_returnsCorrectPrice(
        self,
        mock_get_product_price: Mock,
        mock_get_number_of_months_in_growing_period: Mock,
    ):
        subscription, product = self.setup_mocks(mock_get_product_price)
        date = datetime.date(year=2020, month=5, day=7)  # 2020 has 53 weeks

        result = DeliveryPriceCalculator.get_price_of_single_delivery_for_subscription(
            subscription, date, cache={}
        )

        self.assert_correct(
            result=result,
            product=product,
            date=date,
            nb_weeks=53,
            mock_get_product_price=mock_get_product_price,
            mock_get_number_of_months_in_growing_period=mock_get_number_of_months_in_growing_period,
        )

    @patch.object(
        DeliveryPriceCalculator, "get_number_of_months_in_growing_period", autospec=True
    )
    @patch(
        "tapir.subscriptions.services.delivery_price_calculator.get_product_price",
        autospec=True,
    )
    def test_getPriceOfSingleDelivery_subscriptionHasQuantityHigherThanOne_returnsPriceTakingQuantityIntoAccount(
        self,
        mock_get_product_price: Mock,
        mock_get_number_of_months_in_growing_period: Mock,
    ):
        # Regression test for support ticket GBK#210 where the price of a single delivery would not take the quantity field into account
        # https://support.foodcoopx.de/conversation/210

        subscription, product = self.setup_mocks(mock_get_product_price)
        subscription.quantity = 3
        date = datetime.date(year=2021, month=5, day=7)  # 2021 has 52 weeks

        result = DeliveryPriceCalculator.get_price_of_single_delivery_for_subscription(
            subscription, date, cache={}
        )

        # 10€ monthly price, 3 for the quantity, 12 months in a year and 52 weeks in that year
        # 10 * 3 * 12 / 52 = 6.92...
        self.assertEqual(Decimal("6.92"), result.quantize(Decimal("0.01")))

    @classmethod
    def setup_mocks(cls, mock_get_product_price: Mock):
        price_object = Mock()
        price_object.price = Decimal("10.00")
        mock_get_product_price.return_value = price_object

        subscription = Mock()
        product = Mock()
        subscription.product = product
        growing_period = Mock()
        subscription.period = growing_period
        subscription.product.type.delivery_cycle = "weekly"
        subscription.quantity = 1

        return subscription, product

    def assert_correct(
        self,
        result,
        product,
        date,
        nb_weeks: int,
        mock_get_product_price,
        mock_get_number_of_months_in_growing_period,
    ):
        self.assertEqual(
            Decimal(10 * 12 / nb_weeks).quantize(Decimal("0.01")),
            result.quantize(Decimal("0.01")),
        )

        mock_get_product_price.assert_called_once_with(product, date, cache={})
        mock_get_number_of_months_in_growing_period.assert_not_called()
