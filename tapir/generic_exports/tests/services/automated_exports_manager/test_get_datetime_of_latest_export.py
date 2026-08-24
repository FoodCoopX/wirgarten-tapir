from unittest.mock import patch, Mock

from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.generic_exports.models import AutomatedExportCycle
from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetDatetimeOfLatestExport(TapirUnitTest):
    @patch.object(
        AutomatedExportsManager,
        "get_datetime_of_latest_export_after_pickup_location_change_deadline",
    )
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsYearly_getsResultFromYearlyFunction(
        self,
        mock_yearly: Mock,
        mock_monthly: Mock,
        mock_weekly: Mock,
        mock_daily: Mock,
        mock_after_deadline: Mock,
    ):
        export = Mock()
        export.automated_export_cycle = AutomatedExportCycle.YEARLY
        expected = Mock()
        mock_yearly.return_value = expected

        result = AutomatedExportsManager.get_datetime_of_latest_export(
            export, cache=Mock()
        )

        self.assertEqual(expected, result)
        mock_yearly.assert_called_once_with(export)
        for mock in [mock_monthly, mock_weekly, mock_daily, mock_after_deadline]:
            mock.assert_not_called()

    @patch.object(
        AutomatedExportsManager,
        "get_datetime_of_latest_export_after_pickup_location_change_deadline",
    )
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsMonthly_getsResultFromMonthlyFunction(
        self,
        mock_yearly: Mock,
        mock_monthly: Mock,
        mock_weekly: Mock,
        mock_daily: Mock,
        mock_after_deadline: Mock,
    ):
        export = Mock()
        export.automated_export_cycle = AutomatedExportCycle.MONTHLY
        expected = Mock()
        mock_monthly.return_value = expected

        result = AutomatedExportsManager.get_datetime_of_latest_export(
            export, cache=Mock()
        )

        self.assertEqual(expected, result)
        mock_monthly.assert_called_once_with(export)
        for mock in [mock_yearly, mock_weekly, mock_daily, mock_after_deadline]:
            mock.assert_not_called()

    @patch.object(
        AutomatedExportsManager,
        "get_datetime_of_latest_export_after_pickup_location_change_deadline",
    )
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsWeekly_getsResultFromWeeklyFunction(
        self,
        mock_yearly: Mock,
        mock_monthly: Mock,
        mock_weekly: Mock,
        mock_daily: Mock,
        mock_after_deadline: Mock,
    ):
        export = Mock()
        export.automated_export_cycle = AutomatedExportCycle.WEEKLY
        expected = Mock()
        mock_weekly.return_value = expected

        result = AutomatedExportsManager.get_datetime_of_latest_export(
            export, cache=Mock()
        )

        self.assertEqual(expected, result)
        mock_weekly.assert_called_once_with(export)
        for mock in [mock_yearly, mock_monthly, mock_daily, mock_after_deadline]:
            mock.assert_not_called()

    @patch.object(
        AutomatedExportsManager,
        "get_datetime_of_latest_export_after_pickup_location_change_deadline",
    )
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsDaily_getsResultFromDailyFunction(
        self,
        mock_yearly: Mock,
        mock_monthly: Mock,
        mock_weekly: Mock,
        mock_daily: Mock,
        mock_after_deadline: Mock,
    ):
        export = Mock()
        export.automated_export_cycle = AutomatedExportCycle.DAILY
        expected = Mock()
        mock_daily.return_value = expected

        result = AutomatedExportsManager.get_datetime_of_latest_export(
            export, cache=Mock()
        )

        self.assertEqual(expected, result)
        mock_daily.assert_called_once_with(export)
        for mock in [mock_yearly, mock_monthly, mock_weekly, mock_after_deadline]:
            mock.assert_not_called()

    @patch.object(
        AutomatedExportsManager,
        "get_datetime_of_latest_export_after_pickup_location_change_deadline",
    )
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsAfterDeadline_getsResultFromDeadlineFunction(
        self,
        mock_yearly: Mock,
        mock_monthly: Mock,
        mock_weekly: Mock,
        mock_daily: Mock,
        mock_after_deadline: Mock,
    ):
        export = Mock()
        export.automated_export_cycle = (
            AutomatedExportCycle.AFTER_PICKUP_LOCATION_CHANGE_DEADLINE
        )
        expected = Mock()
        mock_after_deadline.return_value = expected
        cache = {"some": "cache"}

        result = AutomatedExportsManager.get_datetime_of_latest_export(
            export, cache=cache
        )

        self.assertEqual(expected, result)
        mock_after_deadline.assert_called_once_with(export, cache=cache)
        for mock in [mock_yearly, mock_monthly, mock_weekly, mock_daily]:
            mock.assert_not_called()

    @patch.object(
        AutomatedExportsManager,
        "get_datetime_of_latest_export_after_pickup_location_change_deadline",
    )
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_daily_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_weekly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_monthly_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_yearly_export")
    def test_getDatetimeOfLatestExport_exportIsNever_raisesError(
        self,
        mock_yearly: Mock,
        mock_monthly: Mock,
        mock_weekly: Mock,
        mock_daily: Mock,
        mock_after_deadline: Mock,
    ):
        export = Mock()
        export.automated_export_cycle = AutomatedExportCycle.NEVER

        with self.assertRaises(TapirImproperlyConfigured):
            AutomatedExportsManager.get_datetime_of_latest_export(export, cache=Mock())

        for mock in [
            mock_yearly,
            mock_monthly,
            mock_weekly,
            mock_daily,
            mock_after_deadline,
        ]:
            mock.assert_not_called()
