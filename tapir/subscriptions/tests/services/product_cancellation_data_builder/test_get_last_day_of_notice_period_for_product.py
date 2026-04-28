import datetime
from unittest.mock import Mock, call, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.product_cancellation_data_builder import (
    ProductCancellationDataBuilder,
)


class ProductCancellationDataBuilderGetLastDayOfNoticePeriodForProduct(
    TapirUnitTest,
):
    @patch.object(
        NoticePeriodManager,
        "get_max_cancellation_date_subscription",
        autospec=True,
    )
    def test_getLastDayOfNoticePeriodForProduct_singleSubscription_returnsNoticePeriodEnd(
        self,
        mock_get_max_cancellation_date_subscription: Mock,
    ):
        cache = {}
        mock_subscription = Mock()
        mock_notice_period_end = datetime.date(2026, 6, 1)
        mock_get_max_cancellation_date_subscription.return_value = (
            mock_notice_period_end
        )

        result = (
            ProductCancellationDataBuilder.get_last_day_of_notice_period_for_product(
                product_subscriptions=[mock_subscription], cache=cache
            )
        )

        self.assertEqual(mock_notice_period_end, result)
        mock_get_max_cancellation_date_subscription.assert_called_once_with(
            subscription=mock_subscription, cache=cache
        )

    @patch.object(
        NoticePeriodManager,
        "get_max_cancellation_date_subscription",
        autospec=True,
    )
    def test_getLastDayOfNoticePeriodForProduct_multipleSubscriptions_returnsLatestNoticePeriodEnd(
        self,
        mock_get_max_cancellation_date_subscription: Mock,
    ):
        cache = {}
        mock_subscription_a = Mock()
        mock_subscription_b = Mock()
        mock_notice_period_end_early = datetime.date(2026, 5, 1)
        mock_notice_period_end_late = datetime.date(2026, 7, 1)
        mock_get_max_cancellation_date_subscription.side_effect = [
            mock_notice_period_end_early,
            mock_notice_period_end_late,
        ]

        result = (
            ProductCancellationDataBuilder.get_last_day_of_notice_period_for_product(
                product_subscriptions=[mock_subscription_a, mock_subscription_b],
                cache=cache,
            )
        )

        self.assertEqual(mock_notice_period_end_late, result)
        self.assertEqual(2, mock_get_max_cancellation_date_subscription.call_count)
        mock_get_max_cancellation_date_subscription.assert_has_calls(
            [
                call(subscription=mock_subscription_a, cache=cache),
                call(subscription=mock_subscription_b, cache=cache),
            ],
            any_order=True,
        )
