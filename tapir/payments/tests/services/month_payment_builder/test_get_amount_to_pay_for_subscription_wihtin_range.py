from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)


class TestGetAmountToPayForSubscriptionWithinRange(SimpleTestCase):
    @patch.object(
        DeliveryPriceCalculator, "get_price_of_single_delivery_without_solidarity"
    )
    @patch.object(MonthPaymentBuilder, "get_number_of_months_and_deliveries_to_pay")
    def test_getAmountToPayForSubscriptionWithinRange_default_returnsCorrectPrice(
        self,
        mock_get_number_of_months_and_deliveries_to_pay: Mock,
        mock_get_price_of_single_delivery_without_solidarity: Mock,
    ):
        mock_get_number_of_months_and_deliveries_to_pay.return_value = 3, 4
        mock_get_price_of_single_delivery_without_solidarity.return_value = 2.15

        subscription = Mock()
        subscription.total_price = Mock()
        subscription.total_price.return_value = 14.5

        range_start = Mock()
        range_end = Mock()
        cache = Mock()

        result = MonthPaymentBuilder.get_amount_to_pay_for_subscription_within_range(
            subscription=subscription,
            range_start=range_start,
            range_end=range_end,
            cache=cache,
        )

        self.assertEqual(
            3 * 14.5 + 4 * 2.15, result
        )  # 3 full months * 14.5 total price + 4 deliveries + 2.15 delivery price

        mock_get_number_of_months_and_deliveries_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            subscription=subscription,
            cache=cache,
        )
        subscription.total_price.assert_called_once_with(
            reference_date=range_start, cache=cache
        )
        mock_get_price_of_single_delivery_without_solidarity.assert_called_once_with(
            subscription=subscription, at_date=range_start, cache=cache
        )
