from unittest.mock import Mock, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.product_cancellation_data_builder import (
    ProductCancellationDataBuilder,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class ProductCancellationDataBuilderGetDateLimitForTrialCancellation(TapirUnitTest):
    @patch.object(
        ProductCancellationDataBuilder,
        "get_date_limit_for_trial_cancellation_fixed_mode",
        autospec=True,
    )
    @patch.object(
        ProductCancellationDataBuilder,
        "get_date_limit_for_trial_cancellation_flexible_mode",
        autospec=True,
    )
    def test_getDateLimitForTrialCancellation_trialPeriodIsFlexible_returnsDateFromFlexibleMode(
        self,
        mock_get_date_limit_for_trial_cancellation_flexible_mode: Mock,
        mock_get_date_limit_for_trial_cancellation_fixed_mode: Mock,
    ):
        cache = {}
        mock_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END,
            cache=cache,
            value=True,
        )
        mock_product_subscriptions = Mock()
        mock_date_limit = Mock()
        mock_get_date_limit_for_trial_cancellation_flexible_mode.return_value = (
            mock_date_limit
        )

        result = ProductCancellationDataBuilder.get_date_limit_for_trial_cancellation(
            product_subscriptions=mock_product_subscriptions, cache=cache
        )

        self.assertEqual(mock_date_limit, result)
        mock_get_date_limit_for_trial_cancellation_flexible_mode.assert_called_once_with(
            cache=cache
        )
        mock_get_date_limit_for_trial_cancellation_fixed_mode.assert_not_called()

    @patch.object(
        ProductCancellationDataBuilder,
        "get_date_limit_for_trial_cancellation_flexible_mode",
        autospec=True,
    )
    @patch.object(
        ProductCancellationDataBuilder,
        "get_date_limit_for_trial_cancellation_fixed_mode",
        autospec=True,
    )
    def test_getDateLimitForTrialCancellation_trialPeriodIsNotFlexible_returnsDateFromFixedMode(
        self,
        mock_get_date_limit_for_trial_cancellation_fixed_mode: Mock,
        mock_get_date_limit_for_trial_cancellation_flexible_mode: Mock,
    ):
        cache = {}
        mock_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END,
            cache=cache,
            value=False,
        )
        mock_product_subscriptions = Mock()
        mock_date_limit = Mock()
        mock_get_date_limit_for_trial_cancellation_fixed_mode.return_value = (
            mock_date_limit
        )

        result = ProductCancellationDataBuilder.get_date_limit_for_trial_cancellation(
            product_subscriptions=mock_product_subscriptions, cache=cache
        )

        self.assertEqual(mock_date_limit, result)
        mock_get_date_limit_for_trial_cancellation_fixed_mode.assert_called_once_with(
            product_subscriptions=mock_product_subscriptions, cache=cache
        )
        mock_get_date_limit_for_trial_cancellation_flexible_mode.assert_not_called()
