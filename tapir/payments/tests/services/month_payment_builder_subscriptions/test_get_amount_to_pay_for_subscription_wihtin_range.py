from decimal import Decimal
from unittest.mock import patch, Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)


class TestGetAmountToPayForSubscriptionWithinRange(TapirUnitTest):
    @patch.object(
        DeliveryPriceCalculator, "get_price_of_single_delivery_for_subscription"
    )
    @patch.object(
        MonthPaymentBuilderSubscriptions, "get_number_of_months_and_deliveries_to_pay"
    )
    def test_getAmountToPayForSubscriptionWithinRange_default_returnsCorrectPrice(
        self,
        mock_get_number_of_months_and_deliveries_to_pay: Mock,
        mock_get_price_of_single_delivery_for_subscription: Mock,
    ):
        mock_get_number_of_months_and_deliveries_to_pay.return_value = 3, 4
        mock_get_price_of_single_delivery_for_subscription.return_value = Decimal(
            "2.15"
        )

        subscription = Mock()
        subscription.total_price = Mock()
        subscription.total_price.return_value = Decimal("14.5")

        range_start = Mock()
        range_end = Mock()
        cache = Mock()

        result = MonthPaymentBuilderSubscriptions.get_amount_to_pay_for_subscription_within_range(
            subscription=subscription,
            range_start=range_start,
            range_end=range_end,
            cache=cache,
        )

        self.assertEqual(
            Decimal("52.10"), result
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
        mock_get_price_of_single_delivery_for_subscription.assert_called_once_with(
            subscription=subscription, at_date=range_start, cache=cache
        )
