import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestShouldValidateCannotReduceSize(SimpleTestCase):
    def test_shouldValidateCannotReduceSize_loggedInAsAdmin_returnsFalse(self):
        self.assertFalse(
            SubscriptionChangeValidator.should_validate_cannot_reduce_size(
                logged_in_user_is_admin=True,
                subscription_start_date=Mock(),
                cache=Mock(),
            )
        )

    @patch.object(TapirCache, "get_growing_period_at_date")
    def test_shouldValidateCannotReduceSize_noGrowingPeriodAtGivenDate_returnsFalse(
        self, mock_get_growing_period_at_date: Mock
    ):
        subscription_start_date = Mock()
        cache = Mock()
        mock_get_growing_period_at_date.return_value = None

        self.assertFalse(
            SubscriptionChangeValidator.should_validate_cannot_reduce_size(
                logged_in_user_is_admin=False,
                subscription_start_date=subscription_start_date,
                cache=cache,
            )
        )

        mock_get_growing_period_at_date.assert_called_once_with(
            reference_date=subscription_start_date, cache=cache
        )

    @patch.object(TapirCache, "get_growing_period_at_date")
    def test_shouldValidateCannotReduceSize_growingPeriodAtStartDateIsInTheFuture_returnsFalse(
        self, mock_get_growing_period_at_date: Mock
    ):
        subscription_start_date = Mock()
        cache = Mock()
        growing_period = Mock()
        growing_period.start_date = datetime.date(year=2024, month=6, day=1)
        mock_timezone(self, datetime.datetime(year=2024, month=5, day=1))
        mock_get_growing_period_at_date.return_value = growing_period

        self.assertFalse(
            SubscriptionChangeValidator.should_validate_cannot_reduce_size(
                logged_in_user_is_admin=False,
                subscription_start_date=subscription_start_date,
                cache=cache,
            )
        )

        mock_get_growing_period_at_date.assert_called_once_with(
            reference_date=subscription_start_date, cache=cache
        )

    @patch.object(TapirCache, "get_growing_period_at_date")
    def test_shouldValidateCannotReduceSize_growingPeriodAtStartDateIsNotInTheFuture_returnsTrue(
        self, mock_get_growing_period_at_date: Mock
    ):
        subscription_start_date = Mock()
        cache = Mock()
        growing_period = Mock()
        growing_period.start_date = datetime.date(year=2024, month=4, day=1)
        mock_timezone(self, datetime.datetime(year=2024, month=5, day=1))
        mock_get_growing_period_at_date.return_value = growing_period

        self.assertTrue(
            SubscriptionChangeValidator.should_validate_cannot_reduce_size(
                logged_in_user_is_admin=False,
                subscription_start_date=subscription_start_date,
                cache=cache,
            )
        )

        mock_get_growing_period_at_date.assert_called_once_with(
            reference_date=subscription_start_date, cache=cache
        )
