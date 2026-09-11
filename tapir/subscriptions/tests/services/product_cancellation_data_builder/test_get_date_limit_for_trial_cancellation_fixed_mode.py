import datetime
from unittest.mock import Mock, patch, call

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.subscriptions.services.product_cancellation_data_builder import (
    ProductCancellationDataBuilder,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager


class ProductCancellationDataBuilderGetDateLimitForTrialCancellationFixedMode(
    TapirUnitTest,
):
    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
        autospec=True,
    )
    @patch.object(
        TrialPeriodManager,
        "get_last_day_of_trial_period",
        autospec=True,
    )
    def test_getDateLimitForTrialCancellationFixedMode_singleSubscription_returnsDateLimitBasedOnTrialEnd(
        self,
        mock_get_last_day_of_trial_period: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
    ):
        cache = {}
        mock_subscription = Mock()
        mock_trial_end = datetime.date(2026, 5, 1)
        mock_get_last_day_of_trial_period.return_value = mock_trial_end
        mock_date_limit = Mock()
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = (
            mock_date_limit
        )

        result = ProductCancellationDataBuilder.get_date_limit_for_trial_cancellation_fixed_mode(
            product_subscriptions=[mock_subscription], cache=cache
        )

        self.assertEqual(mock_date_limit, result)
        mock_get_last_day_of_trial_period.assert_called_once_with(
            contract=mock_subscription, cache=cache
        )
        mock_calculate_date_limit_for_delivery_changes_in_week.assert_called_once_with(
            mock_trial_end, cache=cache
        )

    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
        autospec=True,
    )
    @patch.object(
        TrialPeriodManager,
        "get_last_day_of_trial_period",
        autospec=True,
    )
    def test_getDateLimitForTrialCancellationFixedMode_multipleSubscriptions_usesEarliestTrialEnd(
        self,
        mock_get_last_day_of_trial_period: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
    ):
        cache = {}
        mock_subscription_a = Mock()
        mock_subscription_b = Mock()
        mock_trial_end_early = datetime.date(2026, 4, 15)
        mock_trial_end_late = datetime.date(2026, 6, 1)
        mock_get_last_day_of_trial_period.side_effect = [
            mock_trial_end_late,
            mock_trial_end_early,
        ]
        mock_date_limit = Mock()
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = (
            mock_date_limit
        )

        result = ProductCancellationDataBuilder.get_date_limit_for_trial_cancellation_fixed_mode(
            product_subscriptions=[mock_subscription_a, mock_subscription_b],
            cache=cache,
        )

        self.assertEqual(mock_date_limit, result)
        self.assertEqual(2, mock_get_last_day_of_trial_period.call_count)
        mock_get_last_day_of_trial_period.assert_has_calls(
            [
                call(contract=mock_subscription_a, cache=cache),
                call(contract=mock_subscription_b, cache=cache),
            ],
            any_order=True,
        )
        mock_calculate_date_limit_for_delivery_changes_in_week.assert_called_once_with(
            mock_trial_end_early, cache=cache
        )

    @patch.object(
        TrialPeriodManager,
        "get_last_day_of_trial_period",
        autospec=True,
    )
    def test_getDateLimitForTrialCancellationFixedMode_noneOfTheSubscriptionIsOnTrial_usesEarliestTrialEnd(
        self,
        mock_get_last_day_of_trial_period: Mock,
    ):
        cache = {}
        mock_subscription_a = Mock()
        mock_subscription_b = Mock()
        mock_get_last_day_of_trial_period.return_value = None

        result = ProductCancellationDataBuilder.get_date_limit_for_trial_cancellation_fixed_mode(
            product_subscriptions=[mock_subscription_a, mock_subscription_b],
            cache=cache,
        )

        self.assertIsNone(result)
        self.assertEqual(2, mock_get_last_day_of_trial_period.call_count)
        mock_get_last_day_of_trial_period.assert_has_calls(
            [
                call(contract=mock_subscription_a, cache=cache),
                call(contract=mock_subscription_b, cache=cache),
            ],
            any_order=True,
        )
