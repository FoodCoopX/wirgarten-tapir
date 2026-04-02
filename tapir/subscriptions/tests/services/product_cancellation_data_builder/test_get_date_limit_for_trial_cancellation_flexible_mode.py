import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.subscriptions.services.product_cancellation_data_builder import (
    ProductCancellationDataBuilder,
)
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestProductCancellationDataBuilderGetDataLimitForTrialCancellationFlexibleMode(
    SimpleTestCase,
):
    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
        autospec=True,
    )
    @patch(
        "tapir.subscriptions.services.product_cancellation_data_builder.get_next_delivery_date",
        autospec=True,
    )
    def test_getDateLimitForTrialCancellationFlexibleMode_dateLimitIsInTheFuture_returnsDateLimit(
        self,
        mock_get_next_delivery_date: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
    ):
        cache = {}
        mock_next_delivery_date = Mock()
        mock_get_next_delivery_date.return_value = mock_next_delivery_date
        mock_date_limit = datetime.date(2026, 4, 10)
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = (
            mock_date_limit
        )
        mock_timezone(test=self, now=datetime.datetime(2026, 4, 5))

        result = ProductCancellationDataBuilder.get_date_limit_for_trial_cancellation_flexible_mode(
            cache=cache
        )

        self.assertEqual(mock_date_limit, result)
        mock_get_next_delivery_date.assert_called_once_with(cache=cache)
        mock_calculate_date_limit_for_delivery_changes_in_week.assert_called_once_with(
            mock_next_delivery_date, cache=cache
        )

    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
        autospec=True,
    )
    @patch(
        "tapir.subscriptions.services.product_cancellation_data_builder.get_next_delivery_date",
        autospec=True,
    )
    def test_getDateLimitForTrialCancellationFlexibleMode_dateLimitIsToday_returnsDateLimit(
        self,
        mock_get_next_delivery_date: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
    ):
        cache = {}
        mock_next_delivery_date = Mock()
        mock_get_next_delivery_date.return_value = mock_next_delivery_date
        mock_date_limit = datetime.date(2026, 4, 10)
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = (
            mock_date_limit
        )
        mock_timezone(test=self, now=datetime.datetime(2026, 4, 10))

        result = ProductCancellationDataBuilder.get_date_limit_for_trial_cancellation_flexible_mode(
            cache=cache
        )

        self.assertEqual(mock_date_limit, result)

    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
        autospec=True,
    )
    @patch(
        "tapir.subscriptions.services.product_cancellation_data_builder.get_next_delivery_date",
        autospec=True,
    )
    def test_getDateLimitForTrialCancellationFlexibleMode_dateLimitIsInThePast_returnsDateLimitPlusSevenDays(
        self,
        mock_get_next_delivery_date: Mock,
        mock_calculate_date_limit_for_delivery_changes_in_week: Mock,
    ):
        cache = {}
        mock_next_delivery_date = Mock()
        mock_get_next_delivery_date.return_value = mock_next_delivery_date
        mock_date_limit = datetime.date(2026, 4, 3)
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = (
            mock_date_limit
        )
        mock_timezone(test=self, now=datetime.datetime(2026, 4, 5))

        result = ProductCancellationDataBuilder.get_date_limit_for_trial_cancellation_flexible_mode(
            cache=cache
        )

        self.assertEqual(datetime.date(2026, 4, 10), result)
