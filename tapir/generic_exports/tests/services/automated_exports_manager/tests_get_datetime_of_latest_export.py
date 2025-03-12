from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.generic_exports.models import CsvExport
from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)


class TestGetDatetimeOfLatestExport(SimpleTestCase):
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsYearly_getsResultFromYearlyFunction(
        self, mock_yearly: Mock, mock_monthly: Mock, mock_weekly: Mock, mock_daily: Mock
    ):
        export = Mock()
        export.automated_export_cycle = CsvExport.AutomatedExportCycle.YEARLY
        expected = Mock()
        mock_yearly.return_value = expected

        result = AutomatedExportsManager.get_datetime_of_latest_export(export)

        self.assertEqual(expected, result)
        mock_yearly.assert_called_once_with(export)
        for mock in [mock_monthly, mock_weekly, mock_daily]:
            mock.assert_not_called()

    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsMonthly_getsResultFromMonthlyFunction(
        self, mock_yearly: Mock, mock_monthly: Mock, mock_weekly: Mock, mock_daily: Mock
    ):
        export = Mock()
        export.automated_export_cycle = CsvExport.AutomatedExportCycle.MONTHLY
        expected = Mock()
        mock_monthly.return_value = expected

        result = AutomatedExportsManager.get_datetime_of_latest_export(export)

        self.assertEqual(expected, result)
        mock_monthly.assert_called_once_with(export)
        for mock in [mock_yearly, mock_weekly, mock_daily]:
            mock.assert_not_called()

    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsWeekly_getsResultFromWeeklyFunction(
        self, mock_yearly: Mock, mock_monthly: Mock, mock_weekly: Mock, mock_daily: Mock
    ):
        export = Mock()
        export.automated_export_cycle = CsvExport.AutomatedExportCycle.WEEKLY
        expected = Mock()
        mock_weekly.return_value = expected

        result = AutomatedExportsManager.get_datetime_of_latest_export(export)

        self.assertEqual(expected, result)
        mock_weekly.assert_called_once_with(export)
        for mock in [mock_yearly, mock_monthly, mock_daily]:
            mock.assert_not_called()

    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsDaily_getsResultFromDailyFunction(
        self, mock_yearly: Mock, mock_monthly: Mock, mock_weekly: Mock, mock_daily: Mock
    ):
        export = Mock()
        export.automated_export_cycle = CsvExport.AutomatedExportCycle.DAILY
        expected = Mock()
        mock_daily.return_value = expected

        result = AutomatedExportsManager.get_datetime_of_latest_export(export)

        self.assertEqual(expected, result)
        mock_daily.assert_called_once_with(export)
        for mock in [mock_yearly, mock_monthly, mock_weekly]:
            mock.assert_not_called()

    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsNever_returnsNone(
        self, mock_yearly: Mock, mock_monthly: Mock, mock_weekly: Mock, mock_daily: Mock
    ):
        export = Mock()
        export.automated_export_cycle = CsvExport.AutomatedExportCycle.NEVER

        result = AutomatedExportsManager.get_datetime_of_latest_export(export)

        self.assertIsNone(result)
        for mock in [mock_yearly, mock_monthly, mock_weekly, mock_daily]:
            mock.assert_not_called()
