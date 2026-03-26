import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.deliveries.services.custom_cycle_delivery_date_calculator import (
    CustomCycleDeliveryDateCalculator,
)
from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService


class TestIsWeekDeliveredInCustomCycle(SimpleTestCase):
    @staticmethod
    def _build_cache(date, product_type, growing_period, delivered_weeks):
        return {
            "growing_periods_by_date": {date: growing_period},
            "delivery_weeks_by_product_type_and_growing_period": {
                product_type: {growing_period: delivered_weeks}
            },
        }

    @patch.object(
        CustomCycleDeliveryDateCalculator,
        "does_product_type_have_at_least_one_delivery_in_the_future",
    )
    def test_isWeekDeliveredInCustomCycle_weekIsInDeliveredWeeks_returnsTrue(
        self,
        mock_does_product_type_have_at_least_one_delivery_in_the_future: Mock,
    ):
        date = datetime.date(year=2025, month=3, day=10)  # week 11
        product_type = Mock()
        growing_period = Mock()
        cache = self._build_cache(
            date=date,
            product_type=product_type,
            growing_period=growing_period,
            delivered_weeks={11, 15, 19},
        )

        self.assertTrue(
            DeliveryCycleService.is_week_delivered_in_custom_cycle(
                date=date, product_type=product_type, cache=cache
            )
        )

        mock_does_product_type_have_at_least_one_delivery_in_the_future.assert_not_called()

    @patch.object(
        CustomCycleDeliveryDateCalculator,
        "does_product_type_have_at_least_one_delivery_in_the_future",
    )
    def test_isWeekDeliveredInCustomCycle_weekIsNotInDeliveredWeeksAndHasFutureDeliveries_returnsFalse(
        self,
        mock_does_product_type_have_at_least_one_delivery_in_the_future: Mock,
    ):
        date = datetime.date(year=2025, month=3, day=10)  # week 11
        product_type = Mock()
        growing_period = Mock()
        cache = self._build_cache(
            date=date,
            product_type=product_type,
            growing_period=growing_period,
            delivered_weeks={12, 15, 19},
        )
        mock_does_product_type_have_at_least_one_delivery_in_the_future.return_value = (
            True
        )

        self.assertFalse(
            DeliveryCycleService.is_week_delivered_in_custom_cycle(
                date=date, product_type=product_type, cache=cache
            )
        )

        mock_does_product_type_have_at_least_one_delivery_in_the_future.assert_called_once_with(
            product_type=product_type, reference_date=date, cache=cache
        )

    @patch.object(
        CustomCycleDeliveryDateCalculator,
        "does_product_type_have_at_least_one_delivery_in_the_future",
    )
    def test_isWeekDeliveredInCustomCycle_weekIsNotInDeliveredWeeksAndNoFutureDeliveries_returnsTrue(
        self,
        mock_does_product_type_have_at_least_one_delivery_in_the_future: Mock,
    ):
        date = datetime.date(year=2025, month=3, day=10)  # week 11
        product_type = Mock()
        growing_period = Mock()
        cache = self._build_cache(
            date=date,
            product_type=product_type,
            growing_period=growing_period,
            delivered_weeks={12, 15, 19},
        )
        mock_does_product_type_have_at_least_one_delivery_in_the_future.return_value = (
            False
        )

        self.assertTrue(
            DeliveryCycleService.is_week_delivered_in_custom_cycle(
                date=date, product_type=product_type, cache=cache
            )
        )

        mock_does_product_type_have_at_least_one_delivery_in_the_future.assert_called_once_with(
            product_type=product_type, reference_date=date, cache=cache
        )

    @patch.object(
        CustomCycleDeliveryDateCalculator,
        "does_product_type_have_at_least_one_delivery_in_the_future",
    )
    def test_isWeekDeliveredInCustomCycle_noWeeksInPeriodAndNoFutureDeliveries_returnsTrue(
        self,
        mock_does_product_type_have_at_least_one_delivery_in_the_future: Mock,
    ):
        date = datetime.date(year=2025, month=3, day=10)  # week 11
        product_type = Mock()
        growing_period = Mock()
        cache = self._build_cache(
            date=date,
            product_type=product_type,
            growing_period=growing_period,
            delivered_weeks=set(),
        )
        mock_does_product_type_have_at_least_one_delivery_in_the_future.return_value = (
            False
        )

        self.assertTrue(
            DeliveryCycleService.is_week_delivered_in_custom_cycle(
                date=date, product_type=product_type, cache=cache
            )
        )

        mock_does_product_type_have_at_least_one_delivery_in_the_future.assert_called_once_with(
            product_type=product_type, reference_date=date, cache=cache
        )

    @patch.object(
        CustomCycleDeliveryDateCalculator,
        "does_product_type_have_at_least_one_delivery_in_the_future",
    )
    def test_isWeekDeliveredInCustomCycle_dateIsNotAMonday_returnsTrue(
        self,
        mock_does_product_type_have_at_least_one_delivery_in_the_future: Mock,
    ):
        date = datetime.date(year=2025, month=3, day=12)  # Wednesday, still week 11
        product_type = Mock()
        growing_period = Mock()
        cache = self._build_cache(
            date=date,
            product_type=product_type,
            growing_period=growing_period,
            delivered_weeks={11, 15, 19},
        )

        self.assertTrue(
            DeliveryCycleService.is_week_delivered_in_custom_cycle(
                date=date, product_type=product_type, cache=cache
            )
        )

        mock_does_product_type_have_at_least_one_delivery_in_the_future.assert_not_called()
