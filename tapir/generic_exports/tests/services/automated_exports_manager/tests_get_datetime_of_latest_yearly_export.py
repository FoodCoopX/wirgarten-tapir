import datetime
from unittest.mock import Mock

from django.test import SimpleTestCase

from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestGetDatetimeOfLatestYearlyExport(SimpleTestCase):
    def setUp(self):
        mock_timezone(
            self, datetime.datetime(year=2024, month=1, day=5, hour=8, minute=30)
        )

    def test_getDatetimeOfLatestYearlyExport_dateThisYearIsBeforeNow_returnsDateThisYear(
        self,
    ):
        export = Mock()
        export.automated_export_day = 4
        export.automated_export_hour = datetime.time(hour=6, minute=7)

        result = AutomatedExportsManager.get_datetime_of_latest_yearly_export(export)

        self.assertEqual(2024, result.year)
        self.assertEqual(1, result.month)
        self.assertEqual(4, result.day)
        self.assertEqual(6, result.hour)
        self.assertEqual(7, result.minute)

    def test_getDatetimeOfLatestYearlyExport_dateThisYearIsAfterNow_returnsDatePreviousYear(
        self,
    ):
        export = Mock()
        export.automated_export_day = 5
        export.automated_export_hour = datetime.time(hour=8, minute=45)

        result = AutomatedExportsManager.get_datetime_of_latest_yearly_export(export)

        self.assertEqual(2023, result.year)
        self.assertEqual(1, result.month)
        self.assertEqual(5, result.day)
        self.assertEqual(8, result.hour)
        self.assertEqual(45, result.minute)
