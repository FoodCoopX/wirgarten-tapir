import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.deliveries.services.weeks_without_delivery_service import (
    WeeksWithoutDeliveryService,
)
from tapir.wirgarten.models import GrowingPeriod


class TestWeeksWithoutDeliveryService(SimpleTestCase):
    @patch(
        "tapir.deliveries.services.weeks_without_delivery_service.get_current_growing_period"
    )
    def test_isDeliveryCancelledThisWeek_noGrowingPeriod_returnsFalse(
        self, mock_get_current_growing_period: Mock
    ):
        mock_get_current_growing_period.return_value = None
        delivery_date = datetime.date(year=2024, month=7, day=1)

        cache = {}
        result = WeeksWithoutDeliveryService.is_delivery_cancelled_this_week(
            delivery_date, cache=cache
        )

        self.assertFalse(result)
        mock_get_current_growing_period.assert_called_once_with(
            delivery_date, cache=cache
        )

    @patch(
        "tapir.deliveries.services.weeks_without_delivery_service.get_current_growing_period"
    )
    def test_isDeliveryCancelledThisWeek_inputWeekIsNotInCancelledWeekList_returnsFalse(
        self, mock_get_current_growing_period: Mock
    ):
        growing_period = GrowingPeriod()
        growing_period.weeks_without_delivery = [5, 10, 21]
        mock_get_current_growing_period.return_value = growing_period
        delivery_date = datetime.date(year=2024, month=7, day=1)  # KW27

        cache = {}
        result = WeeksWithoutDeliveryService.is_delivery_cancelled_this_week(
            delivery_date, cache=cache
        )

        self.assertFalse(result)
        mock_get_current_growing_period.assert_called_once_with(
            delivery_date, cache=cache
        )

    @patch(
        "tapir.deliveries.services.weeks_without_delivery_service.get_current_growing_period"
    )
    def test_isDeliveryCancelledThisWeek_inputWeekIsInCancelledList_returnsTrue(
        self, mock_get_current_growing_period: Mock
    ):
        growing_period = GrowingPeriod()
        growing_period.weeks_without_delivery = [5, 10, 27]
        mock_get_current_growing_period.return_value = growing_period
        delivery_date = datetime.date(year=2024, month=7, day=1)  # KW 27

        cache = {}
        result = WeeksWithoutDeliveryService.is_delivery_cancelled_this_week(
            delivery_date, cache=cache
        )

        self.assertTrue(result)
        mock_get_current_growing_period.assert_called_once_with(
            delivery_date, cache=cache
        )
