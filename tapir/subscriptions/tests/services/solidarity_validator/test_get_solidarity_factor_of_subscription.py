from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.subscriptions.services.solidarity_validator import SolidarityValidator


class TestGetSolidarityFactorOfSubscription(SimpleTestCase):
    def test_getSolidarityFactorOfSubscription_subscriptionHasAbsoluteValue_returnsAbsoluteValue(
        self,
    ):
        subscription = Mock()
        subscription.solidarity_price_absolute = 12

        result = SolidarityValidator.get_solidarity_factor_of_subscription(
            subscription, reference_date=Mock(), cache=Mock()
        )

        self.assertEqual(12, result)

    def test_getSolidarityFactorOfSubscription_subscriptionHasNeitherSoliValue_returnsZero(
        self,
    ):
        subscription = Mock()
        subscription.solidarity_price_absolute = None
        subscription.solidarity_price_percentage = None

        result = SolidarityValidator.get_solidarity_factor_of_subscription(
            subscription, reference_date=Mock(), cache=Mock()
        )

        self.assertEqual(0, result)

    @patch("tapir.subscriptions.services.solidarity_validator.get_product_price")
    def test_getSolidarityFactorOfSubscription_subscriptionHasPercentageValue_returnsCorrectFactor(
        self, mock_get_product_price: Mock
    ):
        subscription = Mock()
        subscription.solidarity_price_absolute = None
        subscription.solidarity_price_percentage = 0.1
        subscription.quantity = 3
        product = Mock()
        subscription.product = product
        mock_get_product_price.return_value.price = 10
        reference_date = Mock()
        cache = Mock()

        result = SolidarityValidator.get_solidarity_factor_of_subscription(
            subscription, reference_date=reference_date, cache=cache
        )

        self.assertEqual(3, result)

        mock_get_product_price.assert_called_once_with(
            product=product, reference_date=reference_date, cache=cache
        )
