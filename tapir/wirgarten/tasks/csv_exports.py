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


KEY_PRODUCT = "Produkt"
KEY_QUANTITY = "Anzahl"
KEY_VARIANT = "Variante"
KEY_PICKUPLOCATION = "Abholort"
KEY_STREET = "Straße"
KEY_CITY = "Ort"


@shared_task
def export_pick_list_csv():
    """
    Sums the quantity of product variants per pickup location and exports the list as CSV.
    """

    sums = (
        Subscription.objects.filter(product__type__pickup_enabled=True)
        .values(
            "member__pickup_location__name",
            "member__pickup_location__street",
            "member__pickup_location__postcode",
            "member__pickup_location__city",
            "product__type__name",
            "product__name",
        )
        .annotate(quantity_sum=Sum("quantity"))
        .order_by(
            "member__pickup_location__name", "product__type__name", "product__name"
        )
    )

    output, writer = __begin_csv_string(
        [
            KEY_PICKUPLOCATION,
            KEY_STREET,
            KEY_CITY,
            KEY_PRODUCT,
            KEY_VARIANT,
            KEY_QUANTITY,
        ]
    )
    for row in sums:
        writer.writerow(
            {
                KEY_PICKUPLOCATION: row["member__pickup_location__name"],
                KEY_STREET: row["member__pickup_location__street"],
                KEY_CITY: f"""{row["member__pickup_location__postcode"]} {row["member__pickup_location__city"]}""",
                KEY_PRODUCT: row["product__type__name"],
                KEY_VARIANT: row["product__name"],
                KEY_QUANTITY: row["quantity_sum"],
            }
        )

    export_file(
        filename="Kommissionierliste",
        filetype=ExportedFile.FileType.CSV,
        content=bytes("".join(output.csv_string), "utf-8"),
        send_email=get_parameter_value(Parameter.PICK_LIST_SEND_ADMIN_EMAIL),
    )


@shared_task
def export_supplier_list_csv():
    """
    Sums the quantity of product variants exports a list as CSV per product type.
    """

    def create_csv_string(product_type: str):
        product_type = all_product_types[product_type]

        if product_type is None:
            print(
                f"""export_supplier_list_csv(): Ignoring unknown product type value in parameter '{Parameter.SUPPLIER_LIST_PRODUCT_TYPES}': {product_type}. Possible values: {all_product_types.keys}"""
            )
            return None

        now = datetime.now()
        sums = (
            Subscription.objects.filter(
                start_date__lte=now, end_date__gte=now, product__type=product_type
            )
            .order_by("product__name")
            .values("product__name")
            .annotate(quantity_sum=Sum("quantity"))
        )

        output, writer = __begin_csv_string([KEY_PRODUCT, KEY_QUANTITY])

        for variant in sums:
            writer.writerow(
                {
                    KEY_PRODUCT: variant["product__name"],
                    KEY_QUANTITY: variant["quantity_sum"],
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

        if data is not None:
            export_file(
                filename=f"Lieferant_{type_name}",
                filetype=ExportedFile.FileType.CSV,
                content=bytes(data, "utf-8"),
                send_email=get_parameter_value(
                    Parameter.SUPPLIER_LIST_SEND_ADMIN_EMAIL
                ),
            )
