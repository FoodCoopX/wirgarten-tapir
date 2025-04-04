from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.generic_exports.services.export_mail_sender import ExportMailSender
from tapir.wirgarten.service.email import Attachment


class TestSendMailForExport(SimpleTestCase):
    @patch("tapir.generic_exports.services.export_mail_sender.send_email")
    def test_sendMailsForExport_noRecipients_sendMailsNotCalled(
        self, mock_send_email: Mock
    ):
        export_result = Mock()
        export_result.export_definition.email_recipients = []

        ExportMailSender.send_mails_for_export([export_result])

        mock_send_email.assert_not_called()

    @patch("tapir.generic_exports.services.export_mail_sender.mimetypes")
    @patch("tapir.generic_exports.services.export_mail_sender.send_email")
    def test_sendMailsForExport_hasRecipients_sendsMails(
        self, mock_send_email: Mock, mock_mimetypes: Mock
    ):
        export_result = Mock()
        export_result.export_definition.email_recipients = [
            "test_mail_1",
            "test_mail_2",
        ]
        export_result.export_definition.name = "test_definition_name"
        export_result.file.name = "test_file_name"
        export_result.file.file.decode.return_value = "test file content"
        mock_mimetypes.guess_type.return_value = ("test mime type", "unused")

        ExportMailSender.send_mails_for_export([export_result])

        mock_send_email.assert_called_once_with(
            to_email=[
                "test_mail_1",
                "test_mail_2",
            ],
            subject="Automatisiertes Export aus Tapir: test_definition_name",
            content="Anbei die Dateien: test_file_name",
            attachments=[
                Attachment(
                    file_name="test_file_name",
                    content="test file content",
                    mime_type="test mime type",
                )
            ],
        )

        mock_mimetypes.guess_type.assert_called_once_with("test_file_name")
        export_result.file.file.decode.assert_called_once_with("utf-8")
