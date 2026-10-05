import csv

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import ExportedFile
from tapir.wirgarten.parameter_keys import ParameterKeys


class CsvTextBuilder(object):
    def __init__(self):
        self.csv_string = []

    def write(self, row):
        self.csv_string.append(row)


def __send_email(
    file: ExportedFile,
    cache: dict | None = None,
    errors: list[str] | None = None,
):
    filename_long = (
        f"{file.name}_{file.created_at.strftime('%Y%m%d_%H%M%S')}.{file.type}"
    )
    filename_short = f"{file.name}.{file.type}"

    subject = f"{filename_short} ist bereit"
    error_details = ""
    if errors:
        subject = f"{subject} ({len(errors)} Fehler)"
        error_details = f"<p>Es gab {len(error_details)} Fehler: <ul><li>{"</li><li>".join(errors)}</li></ul></p>"

    body = f"<p>Hallo Admin,</p><p>im Anhang findest du die aktuelle {filename_long}.</p>{error_details}<p>(Automatisch von Tapir versendet)</p>"

    email = EmailMultiAlternatives(
        subject=subject,
        body=body,
        to=[get_parameter_value(ParameterKeys.SITE_ADMIN_EMAIL, cache=cache)],
        from_email=settings.EMAIL_HOST_SENDER,
        bcc=(
            [settings.EMAIL_AUTO_BCC]
            if hasattr(settings, "EMAIL_AUTO_BCC") and settings.EMAIL_AUTO_BCC
            else None
        ),
    )
    email.content_subtype = "html"
    email.attach(filename_long, file.file)
    email.send()


def begin_csv_string(field_names: list[str], delimiter: str = ";"):
    """
    Call this to start writing your CSV file.

    :param field_names: the field names which will be written in the header and used for the data map
    :param delimiter: the CSV delimiter to use. Default: ';'
    :return: output: the CsvTextBuilder, writer: the DictWriter
    """

    output = CsvTextBuilder()
    writer = csv.DictWriter(
        output,
        fieldnames=field_names,
        delimiter=delimiter,
        quoting=csv.QUOTE_NONNUMERIC,
    )
    writer.writeheader()
    return output, writer


def export_file(
    filename: str,
    filetype: ExportedFile.FileType,
    content: bytes,
    send_email: bool,
    cache: dict | None = None,
    errors: list[str] | None = None,
) -> ExportedFile:
    file = ExportedFile.objects.create(name=filename, type=filetype, file=content)

    if send_email:
        __send_email(file, cache=cache, errors=errors)

    return file
