from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.wirgarten.models import ExportedFile


class TestCreateExportedFile(SimpleTestCase):
    @patch.object(CsvExportBuilder, "build_csv_export_string")
    @patch.object(CsvExportBuilder, "build_file_name")
    @patch.object(ExportedFile, "objects")
    def test_createExportedFile_default_createsFile(
        self,
        mock_objects: Mock,
        mock_build_file_name: Mock,
        mock_build_csv_export_string: Mock,
    ):
        export = Mock()
        export.file_name = "input_file_name"
        reference_datetime = Mock()
        expected = Mock()
        mock_objects.create.return_value = expected
        mock_build_file_name.return_value = "output_file_name"
        mock_build_csv_export_string.return_value = "file_as_string"

        result = CsvExportBuilder.create_exported_file(export, reference_datetime)

        self.assertEqual(expected, result)
        mock_objects.create.assert_called_once_with(
            name="output_file_name", type="csv", file=bytes("file_as_string", "utf-8")
        )
        mock_build_file_name.assert_called_once_with(
            "input_file_name", reference_datetime
        )
        mock_build_csv_export_string.assert_called_once_with(export, reference_datetime)
