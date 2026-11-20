import datetime
from unittest.mock import Mock, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.product_cancellation_data_builder import (
    ProductCancellationDataBuilder,
)
from tapir.utils.services.tapir_cache import TapirCache


class TestGetPostTrialSubscriptionEndDate(TapirUnitTest):
    @patch.object(TapirCache, "get_first_growing_period_starting_after", autospec=True)
    def test_getPostTrialSubscriptionEndDate_notInTrial_returnsLastSubscriptionEndDate(
        self, mock_get_first_growing_period_starting_after: Mock
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
        mock_get_first_growing_period_starting_after.assert_not_called()

    @patch.object(TapirCache, "get_first_growing_period_starting_after", autospec=True)
    def test_getPostTrialSubscriptionEndDate_inTrialNoticePeriodAfterTrialEnd_returnsLastSubscriptionEndDate(
        self, mock_get_first_growing_period_starting_after: Mock
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
        mock_get_first_growing_period_starting_after.assert_not_called()

    @patch.object(TapirCache, "get_first_growing_period_starting_after", autospec=True)
    def test_getPostTrialSubscriptionEndDate_inTrialNoticePeriodBeforeTrialEnd_returnsNextPeriodEndDate(
        self, mock_get_first_growing_period_starting_after: Mock
    ):
        last_subscription_end_date = datetime.date(2026, 12, 31)
        next_period_end_date = datetime.date(2027, 12, 31)
        mock_next_period = Mock()
        mock_next_period.end_date = next_period_end_date
        mock_get_first_growing_period_starting_after.return_value = mock_next_period

        result = ProductCancellationDataBuilder.get_post_trial_subscription_end_date(
            is_in_trial=True,
            last_day_to_give_notice=datetime.date(2026, 10, 31),
            date_limit_for_trial_cancellation=datetime.date(2026, 11, 22),
            last_subscription_end_date=last_subscription_end_date,
            cache={},
        )

        self.assertEqual(next_period_end_date, result)
        mock_get_first_growing_period_starting_after.assert_called_once_with(
            reference_date=last_subscription_end_date, cache={}
        )

    @patch.object(TapirCache, "get_first_growing_period_starting_after", autospec=True)
    def test_getPostTrialSubscriptionEndDate_inTrialNoticePeriodBeforeTrialEndNoNextPeriod_returnsLastSubscriptionEndDate(
        self, mock_get_first_growing_period_starting_after: Mock
    ):
        last_subscription_end_date = datetime.date(2026, 12, 31)
        mock_get_first_growing_period_starting_after.return_value = None

        result = ProductCancellationDataBuilder.get_post_trial_subscription_end_date(
            is_in_trial=True,
            last_day_to_give_notice=datetime.date(2026, 10, 31),
            date_limit_for_trial_cancellation=datetime.date(2026, 11, 22),
            last_subscription_end_date=last_subscription_end_date,
            cache={},
        )

        self.assertEqual(last_subscription_end_date, result)
        mock_get_first_growing_period_starting_after.assert_called_once_with(
            reference_date=last_subscription_end_date, cache={}
        )
