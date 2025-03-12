from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.generic_exports.models import AutomatedExportResult
from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder


class TestDoExport(SimpleTestCase):
    @patch.object(AutomatedExportResult, "objects")
    @patch.object(CsvExportBuilder, "create_exported_file")
    def test_doExport_default_createsExportedFileAndExportResult(
        self, mock_create_exported_file: Mock, mock_result_objects: Mock
    ):
        export = Mock()
        reference_datetime = Mock()
        created_file = Mock()
        mock_create_exported_file.return_value = created_file

        AutomatedExportsManager.do_export(export, reference_datetime)

        mock_create_exported_file.assert_called_once_with(export, reference_datetime)
        mock_result_objects.create.assert_called_once_with(
            export_definition=export, datetime=reference_datetime, file=created_file
        )
