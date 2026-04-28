import datetime
from unittest.mock import patch, Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)


class TestGetPriceOfSingleDelivery(TapirUnitTest):
    @patch.object(DeliveryPriceCalculator, "get_number_of_months_in_growing_period")
    @patch("tapir.subscriptions.services.delivery_price_calculator.get_product_price")
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

    @patch.object(DeliveryPriceCalculator, "get_number_of_months_in_growing_period")
    @patch("tapir.subscriptions.services.delivery_price_calculator.get_product_price")
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

    @classmethod
    def setup_mocks(cls, mock_get_product_price: Mock):
        price_object = Mock()
        price_object.price = 10
        mock_get_product_price.return_value = price_object

        subscription = Mock()
        product = Mock()
        subscription.product = product
        growing_period = Mock()
        subscription.period = growing_period
        subscription.product.type.delivery_cycle = "weekly"

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
        self.assertEqual(10 * 12 / nb_weeks, result)

        mock_get_product_price.assert_called_once_with(product, date, cache={})
        mock_get_number_of_months_in_growing_period.assert_not_called()
