import csv
from django.utils.translation import gettext_lazy as _

from django.core.mail import EmailMultiAlternatives

from tapir import settings
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import ExportedFile
from tapir.wirgarten.parameters import Parameter


class CsvTextBuilder(object):
    def __init__(self):
        self.csv_string = []

    def write(self, row):
        self.csv_string.append(row)


def __send_email(file: ExportedFile, recipient: str | None = None):
    if recipient is None:
        recipient = [get_parameter_value(Parameter.SITE_ADMIN_EMAIL)]
    else:
        recipient = recipient.split(",")

    filename = f"{file.name}_{file.created_at.strftime('%Y%m%d_%H%M%S')}.{ExportedFile.FileType.CSV.value}"

    email = EmailMultiAlternatives(
        subject=_("{filename} ist bereit").format(
            filename=f"{file.name}.{ExportedFile.FileType.CSV.value}"
        ),
        body=_(
            "Hallo Admin,<br/><br/>im Anhang findest du die aktuelle {filename}.<br/><br/><br/>(Automatisch von Tapir versendet)"
        ).format(filename=filename),
        to=recipient,
        from_email=settings.EMAIL_HOST_SENDER,
    )
    email.content_subtype = "html"
    email.attach(filename, file.file)
    email.send()


def begin_csv_string(field_names: [str], delimiter: str = ";"):
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
    to_email_custom: str | None = None,
) -> ExportedFile:
    """
    Exports binary data as a virtual file to the database. It can be automatically sent per email to the admin (or a custom email address) and it can be downloaded via UI later on.

    :param filename: The base file name without a timestamp (e.g.: Kommissionierliste)
    :param filetype: The type of the file (e.g. ExportedFile.FileType.CSV)
    :param content: The binary data (convert a string like this: bytes("your string", "utf-8")
    :param send_email: If true, an email will be send to the admin email address (Parameter: wirgarten.site.admin_email) or the 'to_email_custom' address if specified
    :param to_email_custom: Comma seperated list of recipient email addresses (e.g. "tim@example.com,john@example.com")
    """

    file = ExportedFile.objects.create(name=filename, type=filetype, file=content)

    if send_email:
        __send_email(file, to_email_custom)

    return file
