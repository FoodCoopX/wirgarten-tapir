import datetime
from unittest.mock import Mock, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.product_cancellation_data_builder import (
    ProductCancellationDataBuilder,
)
from tapir.subscriptions.services import (
    product_cancellation_data_builder as product_cancellation_data_builder_module,
)


class TestGetPostTrialSubscriptionEndDate(TapirUnitTest):
    @patch.object(
        product_cancellation_data_builder_module,
        "get_next_growing_period",
        autospec=True,
    )
    def test_getPostTrialSubscriptionEndDate_notInTrial_returnsLastSubscriptionEndDate(
        self, mock_get_next_growing_period: Mock
    ):
        end_date = datetime.date(2026, 12, 31)
        result = ProductCancellationDataBuilder.get_post_trial_subscription_end_date(
            is_in_trial=False,
            last_day_to_give_notice=datetime.date(2026, 10, 31),
            date_limit_for_trial_cancellation=datetime.date(2027, 1, 31),
            last_subscription_end_date=end_date,
            cache={},
        )
        self.assertEqual(end_date, result)
        mock_get_next_growing_period.assert_not_called()

    @patch.object(
        product_cancellation_data_builder_module,
        "get_next_growing_period",
        autospec=True,
    )
    def test_getPostTrialSubscriptionEndDate_inTrialNoticePeriodAfterTrialEnd_returnsLastSubscriptionEndDate(
        self, mock_get_next_growing_period: Mock
    ):
        end_date = datetime.date(2026, 12, 31)
        result = ProductCancellationDataBuilder.get_post_trial_subscription_end_date(
            is_in_trial=True,
            last_day_to_give_notice=datetime.date(2026, 11, 30),
            date_limit_for_trial_cancellation=datetime.date(2026, 9, 22),
            last_subscription_end_date=end_date,
            cache={},
        )
        self.assertEqual(end_date, result)
        mock_get_next_growing_period.assert_not_called()

    @patch.object(
        product_cancellation_data_builder_module,
        "get_next_growing_period",
        autospec=True,
    )
    def test_getPostTrialSubscriptionEndDate_inTrialNoticePeriodBeforeTrialEnd_returnsNextPeriodEndDate(
        self, mock_get_next_growing_period: Mock
    ):
        last_subscription_end_date = datetime.date(2026, 12, 31)
        next_period_end_date = datetime.date(2027, 12, 31)
        mock_next_period = Mock()
        mock_next_period.end_date = next_period_end_date
        mock_get_next_growing_period.return_value = mock_next_period

        result = ProductCancellationDataBuilder.get_post_trial_subscription_end_date(
            is_in_trial=True,
            last_day_to_give_notice=datetime.date(2026, 10, 31),
            date_limit_for_trial_cancellation=datetime.date(2026, 11, 22),
            last_subscription_end_date=last_subscription_end_date,
            cache={},
        )

        self.assertEqual(next_period_end_date, result)
        mock_get_next_growing_period.assert_called_once_with(
            reference_date=last_subscription_end_date, cache={}
        )

    @patch.object(
        product_cancellation_data_builder_module,
        "get_next_growing_period",
        autospec=True,
    )
    def test_getPostTrialSubscriptionEndDate_inTrialNoticePeriodBeforeTrialEndNoNextPeriod_returnsLastSubscriptionEndDate(
        self, mock_get_next_growing_period: Mock
    ):
        last_subscription_end_date = datetime.date(2026, 12, 31)
        mock_get_next_growing_period.return_value = None

        result = ProductCancellationDataBuilder.get_post_trial_subscription_end_date(
            is_in_trial=True,
            last_day_to_give_notice=datetime.date(2026, 10, 31),
            date_limit_for_trial_cancellation=datetime.date(2026, 11, 22),
            last_subscription_end_date=last_subscription_end_date,
            cache={},
        )

        self.assertEqual(last_subscription_end_date, result)
        mock_get_next_growing_period.assert_called_once_with(
            reference_date=last_subscription_end_date, cache={}
        )
