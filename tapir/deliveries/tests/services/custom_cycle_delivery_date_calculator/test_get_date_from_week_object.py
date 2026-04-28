from unittest.mock import patch, Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.services.custom_cycle_delivery_date_calculator import (
    CustomCycleDeliveryDateCalculator,
)
from tapir.deliveries.tests.factories import CustomCycleScheduledDeliveryWeekFactory
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestGetDateFromWeekObject(TapirUnitTest):
    @patch.object(
        CustomCycleDeliveryDateCalculator, "get_date_from_calendar_week", autospec=True
    )
    def test_getDateFromWeekObject_default_callsGetDateFromCalendarWeek(
        self, mock_get_date_from_calendar_week: Mock
    ):
        growing_period = GrowingPeriodFactory.build()
        week_object = CustomCycleScheduledDeliveryWeekFactory.build(
            calendar_week=13, growing_period=growing_period
        )

        expected_result = Mock()
        mock_get_date_from_calendar_week.return_value = expected_result

        actual_result = CustomCycleDeliveryDateCalculator.get_date_from_scheduled_week(
            scheduled_week=week_object
        )

        self.assertEqual(expected_result, actual_result)
        mock_get_date_from_calendar_week.assert_called_once_with(
            week=13, growing_period=growing_period
        )
