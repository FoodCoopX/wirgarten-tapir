import mimetypes
from typing import List

from tapir.generic_exports.models import AutomatedCsvExportResult
from tapir.wirgarten.service.email import send_email, Attachment


class ExportMailSender:
    @classmethod
    def send_mails_for_export(cls, export_results: List[AutomatedCsvExportResult]):
        # results are assumed to come all from the same definition
        export_definition = export_results[0].export_definition
        if len(export_definition.email_recipients) == 0:
            return

        attachments = [
            Attachment(
                file_name=export_result.file.name,
                content=export_result.file.file.decode("utf-8"),
                mime_type=mimetypes.guess_type(export_result.file.name)[0],
            )
            for export_result in export_results
        ]

        send_email(
            to_email=export_definition.email_recipients,
            subject=f"Automatisiertes Export aus Tapir: {export_definition.name}",
            content=f"Anbei die Dateien: {';'.join([export_result.file.name for export_result in export_results])}",
            attachments=attachments,
        )
