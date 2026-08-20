import datetime
from unittest.mock import Mock

from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


class TestGetDatetimeOfLatestExportAfterPickupLocationChangeDeadline(TapirUnitTest):
    def setUp(self):
        # This is a Friday
        mock_timezone(
            self, datetime.datetime(year=2025, month=1, day=3, hour=8, minute=30)
        )

    def test_getDatetimeOfLatestExportAfterPickupLocationChangeDeadline_deadlineSunday_returnsMondayThisWeekAtConfiguredHour(
        self,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL,
            value=6,
        )
        export = Mock()
        export.automated_export_hour = datetime.time(hour=0, minute=0)

        result = AutomatedExportsManager.get_datetime_of_latest_export_after_pickup_location_change_deadline(
            export, cache=cache
        )

        # Deadline is Sunday, so the export runs on Monday.
        # Today is Friday, so this week's Monday 00:00 is already in the past; we return that Monday.
        self.assertEqual(2024, result.year)
        self.assertEqual(12, result.month)
        self.assertEqual(30, result.day)
        self.assertEqual(0, result.hour)

    def test_getDatetimeOfLatestExportAfterPickupLocationChangeDeadline_deadlineThursday_returnsFridayThisWeekBecauseAlreadyPassed(
        self,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL,
            value=3,
        )
        export = Mock()
        export.automated_export_hour = datetime.time(hour=6, minute=15)

        result = AutomatedExportsManager.get_datetime_of_latest_export_after_pickup_location_change_deadline(
            export, cache=cache
        )

        # Deadline is Thursday, so the export runs on Friday.
        # Now is Friday 08:30 and the export hour is 06:15, so we return this week's Friday.
        self.assertEqual(2025, result.year)
        self.assertEqual(1, result.month)
        self.assertEqual(3, result.day)
        self.assertEqual(6, result.hour)
        self.assertEqual(15, result.minute)

    def test_getDatetimeOfLatestExportAfterPickupLocationChangeDeadline_deadlineFriday_returnsPreviousSaturdayBecauseExportDayStillAhead(
        self,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL,
            value=4,
        )
        export = Mock()
        export.automated_export_hour = datetime.time(hour=0, minute=0)

        result = AutomatedExportsManager.get_datetime_of_latest_export_after_pickup_location_change_deadline(
            export, cache=cache
        )

        # Deadline is Friday, so the export runs on Saturday.
        # Today is Friday, so this week's Saturday is still ahead; use last week's Saturday.
        self.assertEqual(2024, result.year)
        self.assertEqual(12, result.month)
        self.assertEqual(28, result.day)
        self.assertEqual(0, result.hour)
