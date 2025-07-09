import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.subscriptions.views.cancellations import GetCancellationDataView


class TestBuildSubscribedProductsData(SimpleTestCase):
    @patch.object(
        SubscriptionCancellationManager, "get_earliest_possible_cancellation_date"
    )
    @patch.object(TrialPeriodManager, "is_product_in_trial")
    @patch.object(GetCancellationDataView, "get_subscribed_products")
    def test_buildSubscribedProductsData_default_returnsCorrectData(
        self,
        mock_get_subscribed_products: Mock,
        mock_is_product_in_trial: Mock,
        mock_get_earliest_possible_cancellation_date: Mock,
    ):
        subscribed_products = [Mock(), Mock(), Mock()]
        mock_get_subscribed_products.return_value = subscribed_products
        member = Mock()
        mock_is_product_in_trial.side_effect = [False, True, False]
        mock_get_earliest_possible_cancellation_date.side_effect = [
            datetime.date(year=2023, month=1, day=1),
            datetime.date(year=2023, month=1, day=2),
            datetime.date(year=2023, month=1, day=3),
        ]
        cache = {}
        result = GetCancellationDataView.build_subscribed_products_data(
            member, cache=cache
        )

        self.assertEqual(
            [
                {
                    "product": subscribed_products[0],
                    "is_in_trial": False,
                    "cancellation_date": datetime.date(year=2023, month=1, day=1),
                },
                {
                    "product": subscribed_products[1],
                    "is_in_trial": True,
                    "cancellation_date": datetime.date(year=2023, month=1, day=2),
                },
                {
                    "product": subscribed_products[2],
                    "is_in_trial": False,
                    "cancellation_date": datetime.date(year=2023, month=1, day=3),
                },
            ],
            result,
        )

        mock_get_subscribed_products.assert_called_once_with(member, cache=cache)
        self.assertEqual(3, mock_is_product_in_trial.call_count)
        mock_is_product_in_trial.assert_has_calls(
            [call(product, member, cache=cache) for product in subscribed_products]
        )
        self.assertEqual(3, mock_get_earliest_possible_cancellation_date.call_count)
        mock_get_earliest_possible_cancellation_date.assert_has_calls(
            [
                call(product=product, member=member, cache=cache)
                for product in subscribed_products
            ]
        )
