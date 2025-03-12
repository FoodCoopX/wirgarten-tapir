import mimetypes

from tapir.generic_exports.models import AutomatedCsvExportResult
from tapir.wirgarten.service.email import send_email, Attachment


class ExportMailSender:
    @classmethod
    def send_mails_for_export(cls, export_result: AutomatedCsvExportResult):
        if len(export_result.export_definition.email_recipients) == 0:
            return

        mime_type, _ = mimetypes.guess_type(export_result.file.name)
        send_email(
            to_email=export_result.export_definition.email_recipients,
            subject=f"Automatisiertes Export aus Tapir: {export_result.export_definition.name}",
            content=f"Anbei die Datei {export_result.file.name}",
            attachments=[
                Attachment(
                    file_name=export_result.file.name,
                    content=export_result.file.file.decode("utf-8"),
                    mime_type=mime_type,
                )
            ],
        )
