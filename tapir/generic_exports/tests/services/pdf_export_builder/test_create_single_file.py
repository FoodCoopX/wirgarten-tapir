from unittest.mock import patch, Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
from tapir.wirgarten.models import ExportedFile


class TestCreateSingleFile(TapirUnitTest):
    @patch.object(PdfExportBuilder, "render_pdf_weasyprint")
    @patch.object(CsvExportBuilder, "build_file_name")
    @patch.object(ExportedFile, "objects")
    def test_createSingleFile_default_createsFileCorrectly(
        self,
        mock_exported_file_objects: Mock,
        mock_build_file_name: Mock,
        mock_render_pdf_weasyprint: Mock,
    ):
        mock_export = Mock()
        mock_export.file_name = "file {{name}}"
        mock_export.template = "test {{template}}"
        mock_datetime = Mock()
        mock_context = {
            "name": "weasyprint",
        }
        mock_build_file_name.return_value = "built weasyprint"
        mock_pdf_bytes = Mock()
        mock_render_pdf_weasyprint.return_value = mock_pdf_bytes

        PdfExportBuilder.create_single_file(
            mock_export, mock_datetime, mock_context, False
        )

        mock_build_file_name.assert_called_once_with(
            "file weasyprint", mock_datetime, "pdf"
        )
        mock_render_pdf_weasyprint.assert_called_once_with(
            "test {{template}}",  # template replacement occurs within render_pdf_weasyprint
            mock_context,
        )
        mock_exported_file_objects.create.assert_called_once_with(
            name="built weasyprint",
            type=ExportedFile.FileType.PDF,
            file=mock_pdf_bytes,
        )
