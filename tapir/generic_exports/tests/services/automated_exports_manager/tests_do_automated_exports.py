import datetime
from unittest.mock import patch, Mock

from tapir.generic_exports.models import AutomatedCsvExportResult, AutomatedExportCycle
from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.generic_exports.tests.factories import CsvExportFactory, ExportedFileFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDoAutomatedExports(TapirIntegrationTest):
    @patch.object(AutomatedExportsManager, "do_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_export")
    def test_doAutomatedExports_exportHasCycleNever_noExportDone(
        self, mock_get_datetime_of_latest_export: Mock, mock_do_export: Mock
    ):
        CsvExportFactory.create(automated_export_cycle=AutomatedExportCycle.NEVER)

        AutomatedExportsManager.do_automated_exports()

        mock_get_datetime_of_latest_export.assert_not_called()
        mock_do_export.assert_not_called()

    @patch.object(AutomatedExportsManager, "do_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_export")
    def test_doAutomatedExports_alreadyExportedAtTargetDate_noExportDone(
        self, mock_get_datetime_of_latest_export: Mock, mock_do_export: Mock
    ):
        export = CsvExportFactory.create(
            automated_export_cycle=AutomatedExportCycle.DAILY
        )
        target_date = datetime.datetime(year=2023, month=12, day=5)
        mock_get_datetime_of_latest_export.return_value = target_date
        AutomatedCsvExportResult.objects.create(
            export_definition=export,
            datetime=target_date,
            file=ExportedFileFactory.create(),
        )

        AutomatedExportsManager.do_automated_exports()

        mock_get_datetime_of_latest_export.assert_called_once_with(export)
        mock_do_export.assert_not_called()

    @patch.object(AutomatedExportsManager, "do_export")
    @patch.object(AutomatedExportsManager, "get_datetime_of_latest_export")
    def test_doAutomatedExports_noExportAtTargetDate_exportDone(
        self, mock_get_datetime_of_latest_export: Mock, mock_do_export: Mock
    ):
        export = CsvExportFactory.create(
            automated_export_cycle=AutomatedExportCycle.DAILY
        )
        target_date = datetime.datetime(year=2023, month=12, day=5)
        mock_get_datetime_of_latest_export.return_value = target_date
        AutomatedCsvExportResult.objects.create(
            export_definition=export,
            datetime=target_date - datetime.timedelta(days=1),
            file=ExportedFileFactory.create(),
        )

        AutomatedExportsManager.do_automated_exports()

        mock_get_datetime_of_latest_export.assert_called_once_with(export)
        mock_do_export.assert_called_once_with(export, target_date)
