import datetime
from unittest.mock import Mock

from django.test import SimpleTestCase

from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestGetDatetimeOfLatestWeeklyExport(SimpleTestCase):
    def setUp(self):
        mock_timezone(
            self, datetime.datetime(year=2025, month=1, day=3, hour=8, minute=30)
        )

    def test_getDatetimeOfLatestWeeklyExport_dateThisWeekIsBeforeNow_returnsDateThisWeek(
        self,
    ):
        export = Mock()
        export.automated_export_day = 2  # exporting on tuesdays
        export.automated_export_hour = datetime.time(hour=6, minute=7)

        result = AutomatedExportsManager.get_datetime_of_latest_weekly_export(export)

        self.assertEqual(2024, result.year)
        self.assertEqual(12, result.month)
        self.assertEqual(31, result.day)
        self.assertEqual(6, result.hour)
        self.assertEqual(7, result.minute)

    def test_getDatetimeOfLatestWeeklyExport_dateThisWeekIsAfterNow_returnsDatePreviousWeek(
        self,
    ):
        export = Mock()
        export.automated_export_day = 6  # exporting on saturdays
        export.automated_export_hour = datetime.time(hour=9, minute=45)

        result = AutomatedExportsManager.get_datetime_of_latest_weekly_export(export)

        self.assertEqual(2024, result.year)
        self.assertEqual(12, result.month)
        self.assertEqual(28, result.day)
        self.assertEqual(9, result.hour)
        self.assertEqual(45, result.minute)
