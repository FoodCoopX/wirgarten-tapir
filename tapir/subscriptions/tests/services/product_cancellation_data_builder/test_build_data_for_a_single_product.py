from unittest.mock import MagicMock, Mock, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.product_cancellation_data_builder import (
    ProductCancellationDataBuilder,
)
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.tests.factories import SubscriptionFactory


class TestProductCancellationDataBuilderBuildDataForASingleProduct(TapirUnitTest):
    @patch.object(
        ProductCancellationDataBuilder,
        "get_last_day_of_notice_period_for_product",
        autospec=True,
    )
    @patch.object(
        SubscriptionCancellationManager,
        "get_earliest_possible_cancellation_date_for_product",
        autospec=True,
    )
    @patch.object(
        ProductCancellationDataBuilder,
        "get_date_limit_for_trial_cancellation",
        autospec=True,
    )
    @patch.object(
        TrialPeriodManager,
        "is_product_in_trial",
        autospec=True,
    )
    @patch.object(
        ProductCancellationDataBuilder, "get_relevant_subscriptions", autospec=True
    )
    def test_buildDataForASingleProduct_default_returnsCorrectData(
        self,
        mock_get_relevant_subscriptions: Mock,
        mock_is_product_in_trial: Mock,
        mock_get_date_limit_for_trial_cancellation: Mock,
        mock_get_earliest_possible_cancellation_date_for_product: Mock,
        mock_get_last_day_of_notice_period_for_product: Mock,
    ):
        member = Mock()
        product = Mock()
        cache = Mock()

        mock_notice_period_duration = Mock()
        mock_notice_period_unit = Mock()
        mock_end_date = Mock()

        first_subscription, last_subscription = SubscriptionFactory.build_batch(size=2)
        last_subscription.notice_period_duration = mock_notice_period_duration
        last_subscription.notice_period_unit = mock_notice_period_unit
        last_subscription.end_date = mock_end_date

        mock_queryset = MagicMock()
        mock_get_relevant_subscriptions.return_value = mock_queryset
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered
        product_subscriptions = [first_subscription, last_subscription]
        mock_filtered.order_by.return_value = product_subscriptions

        mock_is_in_trial = Mock()
        mock_is_product_in_trial.return_value = mock_is_in_trial

        mock_date_limit_for_trial_cancellation = Mock()
        mock_get_date_limit_for_trial_cancellation.return_value = (
            mock_date_limit_for_trial_cancellation
        )

        mock_cancellation_date = Mock()
        mock_get_earliest_possible_cancellation_date_for_product.return_value = (
            mock_cancellation_date
        )

        mock_last_day_of_notice_period = Mock()
        mock_get_last_day_of_notice_period_for_product.return_value = (
            mock_last_day_of_notice_period
        )

        result = ProductCancellationDataBuilder.build_data_for_a_single_product(
            member=member, product=product, cache=cache
        )

        expected = {
            "product": product,
            "is_in_trial": mock_is_in_trial,
            "date_limit_for_trial_cancellation": mock_date_limit_for_trial_cancellation,
            "cancellation_date": mock_cancellation_date,
            "last_day_of_notice_period": mock_last_day_of_notice_period,
            "notice_period_duration": mock_notice_period_duration,
            "notice_period_unit": mock_notice_period_unit,
            "subscription_end_date": mock_end_date,
        }

        self.assertEqual(expected, result)

        mock_get_relevant_subscriptions.assert_called_once_with(
            member=member, cache=cache
        )
        mock_queryset.filter.assert_called_once_with(product=product)
        mock_filtered.order_by.assert_called_once_with("end_date")

        mock_is_product_in_trial.assert_called_once_with(product, member, cache=cache)
        mock_get_date_limit_for_trial_cancellation.assert_called_once_with(
            product_subscriptions=product_subscriptions, cache=cache
        )
        mock_get_earliest_possible_cancellation_date_for_product.assert_called_once_with(
            product=product, member=member, cache=cache
        )
        mock_get_last_day_of_notice_period_for_product.assert_called_once_with(
            product_subscriptions=product_subscriptions, cache=cache
        )
