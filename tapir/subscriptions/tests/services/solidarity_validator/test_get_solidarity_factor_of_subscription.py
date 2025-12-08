from unittest.mock import Mock

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

        result = SolidarityValidator.get_solidarity_factor_of_subscription(
            subscription, reference_date=Mock(), cache=Mock()
        )

        self.assertEqual(0, result)
