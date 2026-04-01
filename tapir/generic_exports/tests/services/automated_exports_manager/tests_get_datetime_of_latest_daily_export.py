import datetime
from unittest.mock import Mock

from django.test import SimpleTestCase

from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestGetDatetimeOfLatestDailyExport(SimpleTestCase):
    def setUp(self):
        mock_timezone(
            self, datetime.datetime(year=2025, month=1, day=3, hour=8, minute=30)
        )

    def test_getDatetimeOfLatestDailyExport_dateTodayIsBeforeNow_returnsDateToday(
        self,
    ):
        export = Mock()
        export.automated_export_hour = datetime.time(hour=6, minute=7)

        result = AutomatedExportsManager.get_datetime_of_latest_daily_export(export)

        self.assertEqual(2025, result.year)
        self.assertEqual(1, result.month)
        self.assertEqual(3, result.day)
        self.assertEqual(6, result.hour)
        self.assertEqual(7, result.minute)

    def test_getDatetimeOfLatestDailyExport_dateTodayIsAfterNow_returnsDateYesterday(
        self,
    ):
        export = Mock()
        export.automated_export_hour = datetime.time(hour=8, minute=31)

        result = AutomatedExportsManager.get_datetime_of_latest_daily_export(export)

        self.assertEqual(2025, result.year)
        self.assertEqual(1, result.month)
        self.assertEqual(2, result.day)
        self.assertEqual(8, result.hour)
        self.assertEqual(31, result.minute)
