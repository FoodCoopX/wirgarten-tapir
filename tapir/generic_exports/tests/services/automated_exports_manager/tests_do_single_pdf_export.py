from unittest.mock import patch, Mock, call

from tapir.generic_exports.models import AutomatedPdfExportResult
from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.generic_exports.services.export_mail_sender import ExportMailSender
from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDoSinglePdfExport(TapirIntegrationTest):
    @patch.object(ExportMailSender, "send_mails_for_export")
    @patch.object(AutomatedPdfExportResult, "objects")
    @patch.object(PdfExportBuilder, "create_exported_files")
    def test_doSinglePdfExport_default_createsExportedFileAndExportResultAndSendsMail(
        self,
        create_exported_files: Mock,
        mock_result_objects: Mock,
        mock_send_mails_for_export: Mock,
    ):
        export = Mock()
        reference_datetime = Mock()
        created_files = [Mock(), Mock(), Mock()]
        create_exported_files.return_value = created_files
        export_results = [Mock(), Mock(), Mock()]
        mock_result_objects.create.side_effect = export_results

        AutomatedExportsManager.do_single_pdf_export(export, reference_datetime)
        create_exported_files.assert_called_once_with(export, reference_datetime)
        self.assertEqual(3, mock_result_objects.create.call_count)
        mock_result_objects.create.assert_has_calls(
            [
                call(export_definition=export, datetime=reference_datetime, file=file)
                for file in created_files
            ]
        )

        mock_send_mails_for_export.assert_called_once_with(export_results)
