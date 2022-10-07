import csv
from datetime import datetime
from importlib.resources import _

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import ProductType, Subscription, ExportedFile
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
        from_email=get_parameter_value(Parameter.SITE_ADMIN_EMAIL),
    )
    email.content_subtype = "html"
    email.attach(filename, file.file)
    email.send()


def __begin_csv_string(field_names: [str]):
    output = CsvTextBuilder()
    writer = csv.DictWriter(output, fieldnames=field_names, delimiter=";")
    writer.writeheader()
    return output, writer


def export_file(
    filename: str,
    filetype: ExportedFile.FileType,
    content: bytes,
    send_email: bool,
    to_email_custom: str | None = None,
):
    file = ExportedFile.objects.create(name=filename, type=filetype, file=content)

    if send_email:
        __send_email(file, to_email_custom)


@shared_task
def export_supplier_list_csv():
    def create_csv_string(product_type: str):
        product_type = all_product_types[product_type]
        now = datetime.now()
        sums = (
            Subscription.objects.filter(
                start_date__lte=now, end_date__gte=now, product__type=product_type
            )
            .values("product__name")
            .annotate(quantity_sum=Sum("quantity"))
        )

        output, writer = __begin_csv_string(["product", "quantity"])

        for variant in sums:
            writer.writerow(
                {
                    "product": variant["product__name"],
                    "quantity": variant["quantity_sum"],
                }
            )

        return "".join(output.csv_string)

    all_product_types = {pt.name: pt for pt in ProductType.objects.all()}
    include_product_types = get_parameter_value(
        Parameter.SUPPLIER_LIST_PRODUCT_TYPES
    ).split(",")
    for _type_name in include_product_types:
        type_name = _type_name.strip()
        data = create_csv_string(type_name)

        export_file(
            filename=f"Lieferant_{type_name}",
            filetype=ExportedFile.FileType.CSV,
            content=bytes(data, "utf-8"),
            send_email=get_parameter_value(Parameter.SUPPLIER_LIST_SEND_ADMIN_EMAIL),
        )
