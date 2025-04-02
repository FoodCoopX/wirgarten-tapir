import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)


class TestGetPriceOfSingleDelivery(SimpleTestCase):
    @patch.object(DeliveryPriceCalculator, "get_number_of_deliveries_in_growing_period")
    @patch.object(DeliveryPriceCalculator, "get_number_of_months_in_growing_period")
    @patch("tapir.subscriptions.services.delivery_price_calculator.get_product_price")
    def test_getPriceOfSingleDelivery_default_returnsCorrectPrice(
        self,
        mock_get_product_price: Mock,
        mock_get_number_of_months_in_growing_period: Mock,
        mock_get_number_of_deliveries_in_growing_period: Mock,
    ):
        price_object = Mock()
        price_object.price = 12
        mock_get_product_price.return_value = price_object
        mock_get_number_of_months_in_growing_period.return_value = 10
        mock_get_number_of_deliveries_in_growing_period.return_value = 40

        subscription = Mock()
        product = Mock()
        subscription.product = product
        growing_period = Mock()
        subscription.period = growing_period
        date = datetime.date(year=2020, month=5, day=7)
        subscription.product.type.delivery_cycle = "weekly"

        result = (
            DeliveryPriceCalculator.get_price_of_single_delivery_without_solidarity(
                subscription, date
            )
        )

        self.assertEqual(3, result)  # 12 * 10 / 40 = 3

        mock_get_product_price.assert_called_once_with(product, date)
        mock_get_number_of_months_in_growing_period.assert_called_once_with(
            growing_period
        )
        mock_get_number_of_deliveries_in_growing_period.assert_called_once_with(
            growing_period, "weekly"
        )
