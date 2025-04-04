from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
from tapir.wirgarten.models import ExportedFile


class TestCreateSingleFile(SimpleTestCase):
    @patch.object(PdfExportBuilder, "render_pdf")
    @patch.object(CsvExportBuilder, "build_file_name")
    @patch.object(ExportedFile, "objects")
    @patch.object(PdfExportBuilder, "build_template_object")
    def test_createSingleFile_default_createsFileCorrectly(
        self,
        mock_build_template_object: Mock,
        mock_exported_file_objects: Mock,
        mock_build_file_name: Mock,
        mock_render_pdf: Mock,
    ):
        mock_export = Mock()
        mock_export.file_name = "test file name"
        mock_export.template = "test template"
        mock_datetime = Mock()
        mock_context = Mock()
        mock_template_object = Mock()
        mock_template_object.render.return_value = "test rendered file name"
        mock_build_template_object.return_value = mock_template_object
        mock_build_file_name.return_value = "test build file name"
        mock_rendered_pdf = Mock()
        mock_render_pdf.return_value = mock_rendered_pdf
        mock_pdf_bytes = Mock()
        mock_rendered_pdf.write_pdf.return_value = mock_pdf_bytes

        PdfExportBuilder.create_single_file(mock_export, mock_datetime, mock_context)

        mock_build_template_object.assert_called_once_with("test file name")
        mock_template_object.render.assert_called_once_with(mock_context)
        mock_build_file_name.assert_called_once_with(
            "test rendered file name", mock_datetime, "pdf"
        )
        mock_render_pdf.assert_called_once_with("test template", mock_context)
        mock_rendered_pdf.write_pdf.assert_called_once_with()
        mock_exported_file_objects.create.assert_called_once_with(
            name="test build file name",
            type=ExportedFile.FileType.PDF,
            file=mock_pdf_bytes,
        )
