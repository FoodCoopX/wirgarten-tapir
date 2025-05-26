from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.subscriptions.services.solidarity_validator import SolidarityValidator


class TestGetSolidarityExcess(SimpleTestCase):
    @patch.object(SolidarityValidator, "get_solidarity_factor_of_subscription")
    @patch(
        "tapir.subscriptions.services.solidarity_validator.get_active_and_future_subscriptions"
    )
    def test_getSolidarityExcess_default_returnsSumOfSoliFactors(
        self,
        mock_get_active_and_future_subscriptions: Mock,
        mock_get_solidarity_factor_of_subscription: Mock,
    ):
        subscription_1 = Mock()
        subscription_2 = Mock()
        subscription_3 = Mock()

        mock_get_active_and_future_subscriptions.return_value.select_related.return_value = [
            subscription_1,
            subscription_2,
            subscription_3,
        ]

        solidarity_factors_map = {
            subscription_1: 12,
            subscription_2: -5,
            subscription_3: 15,
        }
        mock_get_solidarity_factor_of_subscription.side_effect = (
            lambda subscription, reference_date, cache: solidarity_factors_map[
                subscription
            ]
        )

        reference_date = Mock()
        cache = Mock()
        result = SolidarityValidator.get_solidarity_excess(
            reference_date=reference_date, cache=cache
        )

        self.assertEqual(result, 22)

        mock_get_active_and_future_subscriptions.assert_called_once_with(
            reference_date=reference_date, cache=cache
        )
        mock_get_solidarity_factor_of_subscription.assert_has_calls(
            [
                call(
                    subscription=subscription,
                    reference_date=reference_date,
                    cache=cache,
                )
                for subscription in [
                    subscription_1,
                    subscription_2,
                    subscription_3,
                ]
            ],
            any_order=True,
        )
