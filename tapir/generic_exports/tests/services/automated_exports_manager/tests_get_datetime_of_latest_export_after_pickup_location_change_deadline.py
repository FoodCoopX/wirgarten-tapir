import datetime
from unittest.mock import Mock, patch

from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


class TestGetDatetimeOfLatestExportAfterPickupLocationChangeDeadline(TapirUnitTest):
    def setUp(self):
        # Friday 2025-01-03 08:30
        mock_timezone(
            self, datetime.datetime(year=2025, month=1, day=3, hour=8, minute=30)
        )

    @patch(
        "tapir.generic_exports.services.automated_exports_manager.get_parameter_value"
    )
    def test_deadlineSunday_returnsMondayThisWeekAtConfiguredHour(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.side_effect = lambda key, cache=None: (
            6 if key == ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL else None
        )
        export = Mock()
        export.automated_export_hour = datetime.time(hour=0, minute=0)

        result = AutomatedExportsManager.get_datetime_of_latest_export_after_pickup_location_change_deadline(
            export, cache={}
        )

        # Deadline Sunday -> export Monday. Now is Friday, so Monday this week is future -> previous Monday
        self.assertEqual(2024, result.year)
        self.assertEqual(12, result.month)
        self.assertEqual(30, result.day)
        self.assertEqual(0, result.hour)
        mock_get_parameter_value.assert_called_with(
            ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL, cache={}
        )

    @patch(
        "tapir.generic_exports.services.automated_exports_manager.get_parameter_value"
    )
    def test_deadlineThursday_returnsFridayThisWeekBecauseAlreadyPassed(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.side_effect = lambda key, cache=None: (
            3 if key == ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL else None
        )
        export = Mock()
        export.automated_export_hour = datetime.time(hour=6, minute=15)

        result = AutomatedExportsManager.get_datetime_of_latest_export_after_pickup_location_change_deadline(
            export, cache={}
        )

        # Deadline Thursday (3) -> export Friday (4). Now is Friday 08:30, slot was 06:15 -> this week
        self.assertEqual(2025, result.year)
        self.assertEqual(1, result.month)
        self.assertEqual(3, result.day)
        self.assertEqual(6, result.hour)
        self.assertEqual(15, result.minute)

    @patch(
        "tapir.generic_exports.services.automated_exports_manager.get_parameter_value"
    )
    def test_deadlineFriday_returnsPreviousSaturdayBecauseExportDayStillAhead(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.side_effect = lambda key, cache=None: (
            4 if key == ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL else None
        )
        export = Mock()
        export.automated_export_hour = datetime.time(hour=0, minute=0)

        result = AutomatedExportsManager.get_datetime_of_latest_export_after_pickup_location_change_deadline(
            export, cache={}
        )

        # Deadline Friday (4) -> export Saturday (5). Now is Friday -> Saturday still ahead
        # -> return previous Saturday (2024-12-28)
        self.assertEqual(2024, result.year)
        self.assertEqual(12, result.month)
        self.assertEqual(28, result.day)
        self.assertEqual(0, result.hour)
