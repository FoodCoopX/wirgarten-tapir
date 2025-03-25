from unittest.mock import Mock, patch, call

from django.test import SimpleTestCase

from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)


class TestGetPriceOfSubscriptionsDeliveredInWeek(SimpleTestCase):
    @patch.object(DeliveryPriceCalculator, "get_price_of_single_delivery")
    @patch.object(
        DeliveryPriceCalculator, "get_subscriptions_that_get_delivered_in_week"
    )
    def test_getPriceOfSubscriptionsDeliveredInWeek_default_returnsSumOfPriceTimesQuantity(
        self,
        mock_get_subscriptions_that_get_delivered_in_week: Mock,
        mock_get_price_of_single_delivery: Mock,
    ):
        subscriptions = [Mock(), Mock()]
        subscriptions[0].quantity = 2
        subscriptions[1].quantity = 4
        mock_get_subscriptions_that_get_delivered_in_week.return_value = subscriptions
        mock_get_price_of_single_delivery.side_effect = [15, 26]
        member = Mock()
        reference_date = Mock()

        result = DeliveryPriceCalculator.get_price_of_subscriptions_delivered_in_week(
            member, reference_date
        )

        self.assertEqual(2 * 15 + 4 * 26, result)

        mock_get_subscriptions_that_get_delivered_in_week.assert_called_once_with(
            member, reference_date
        )
        self.assertEqual(2, mock_get_price_of_single_delivery.call_count)
        mock_get_price_of_single_delivery.assert_has_calls(
            [call(subscription, reference_date) for subscription in subscriptions],
            any_order=True,
        )
