import itertools
from collections import defaultdict
from datetime import datetime, date

from celery import shared_task
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.models import (
    ExportedFile,
    Payment,
    Subscription,
    ProductType,
    PaymentTransaction,
    Product,
    PickupLocation,
    Member,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.email import send_email
from tapir.wirgarten.service.file_export import export_file, begin_csv_string
from tapir.wirgarten.service.payment import (
    generate_new_payments,
    get_existing_payments,
)
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_active_subscriptions,
    get_future_subscriptions,
    get_product_price,
)
from tapir.wirgarten.utils import format_date


@shared_task
def export_pick_list_csv():
    """
    Exports a CSV file containing the pick list for the next delivery.
    """

    KEY_EMAIL = "E-Mail"
    KEY_FIRST_NAME = "Vorname"
    KEY_PICKUP_LOCATION = "Abholort"
    KEY_M_EQUIVALENT = "M-Äquivalent"

    base_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
    subscriptions = get_active_subscriptions().filter(product__type_id=base_type_id)
    grouped_subscriptions = defaultdict(list)

    # Populate the dictionary
    for subscription in subscriptions:
        grouped_subscriptions[subscription.member].append(subscription)

    variants = list(Product.objects.filter(type_id=base_type_id))
    variants.sort(key=lambda x: get_product_price(x).price)
    variant_names = [x.name for x in variants]

    output, writer = begin_csv_string(
        [
            KEY_EMAIL,
            KEY_FIRST_NAME,
            *variant_names,
            KEY_PICKUP_LOCATION,
            KEY_M_EQUIVALENT,
        ]
    )

    base_price = get_product_price(
        Product.objects.filter(type_id=base_type_id, base=True).first()
    ).price
    for member, subs in grouped_subscriptions.items():
        subs.sort(key=lambda x: x.product.name)
        grouped_subs = {
            key: f"{sum(map(lambda x: x.quantity, group))} Stück"
            for key, group in itertools.groupby(subs, key=lambda sub: sub.product.name)
        }

        sum_without_soli = sum(map(lambda x: x.total_price_without_soli, subs))
        m_equivalents = round(sum_without_soli / base_price, 2)

        writer.writerow(
            {
                KEY_EMAIL: member.email,
                KEY_FIRST_NAME: member.first_name,
                KEY_PICKUP_LOCATION: member.pickup_location.name,
                KEY_M_EQUIVALENT: m_equivalents,
                **grouped_subs,
            }
        )

    export_file(
        filename="Kommissionierliste",
        filetype=ExportedFile.FileType.CSV,
        content=bytes("".join(output.csv_string), "utf-8"),
        send_email=get_parameter_value(Parameter.PICK_LIST_SEND_ADMIN_EMAIL),
    )


def export_supplier_list_csv():
    """
    Sums the quantity of product variants exports a list as CSV per product type.
    """

    KEY_PRODUCT = "Produkt"
    KEY_QUANTITY = "Anzahl"

    def create_csv_string(product_type: str):
        product_type = all_product_types[product_type]

        if product_type is None:
            print(
                f"""export_supplier_list_csv(): Ignoring unknown product type value in parameter '{Parameter.SUPPLIER_LIST_PRODUCT_TYPES}': {product_type}. Possible values: {all_product_types.keys}"""
            )
            return None

        now = timezone.now()
        sums = (
            Subscription.objects.filter(
                start_date__lte=now, end_date__gte=now, product__type=product_type
            )
            .order_by("product__name")
            .values("product__name")
            .annotate(quantity_sum=Sum("quantity"))
        )

        output, writer = begin_csv_string([KEY_PRODUCT, KEY_QUANTITY])

        for variant in sums:
            writer.writerow(
                {
                    KEY_PRODUCT: variant["product__name"],
                    KEY_QUANTITY: variant["quantity_sum"],
                }
            )

        return "".join(output.csv_string)

    all_product_types = {pt.name: pt for pt in get_active_product_types()}
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


@shared_task
def export_harvest_share_subscriber_emails():
    """
    Exports the names and email addresses of members with active harvest share subscriptions.
    The exported list will be used by the newsletter sender (everyone in the list gets the newsleter).
    """

    KEY_FIRST_NAME = "Vorname"
    KEY_LAST_NAME = "Nachname"
    KEY_VARIANTS = "Ernteanteile"
    KEY_EMAIL = "Email"

    def create_csv_string():
        output, writer = begin_csv_string(
            [KEY_FIRST_NAME, KEY_LAST_NAME, KEY_VARIANTS, KEY_EMAIL]
        )
        for member, subs in itertools.groupby(
            get_active_subscriptions()
            .filter(product__type__name=ProductTypes.HARVEST_SHARES)
            .order_by("member_id"),
            lambda x: x.member,
        ):
            writer.writerow(
                {
                    KEY_FIRST_NAME: member.first_name,
                    KEY_LAST_NAME: member.last_name,
                    KEY_VARIANTS: ", ".join(subs),
                    KEY_EMAIL: member.email,
                }
            )
        return "".join(output.csv_string)

    export_file(
        filename="Erntepost_Empfänger",
        filetype=ExportedFile.FileType.CSV,
        content=bytes(create_csv_string(), "utf-8"),
        send_email=True,
    )


@shared_task
def send_email_member_contract_end_reminder(member_id):
    member = Member.objects.get(pk=member_id)

    today = date.today()
    if (
        get_active_subscriptions().filter(member=member).exists()
        and not get_future_subscriptions()
        .filter(member=member, start_date__gt=today)
        .exists()
    ):

        send_email(
            to_email=[member.email],
            subject=get_parameter_value(Parameter.EMAIL_CONTRACT_END_REMINDER_SUBJECT),
            content=get_parameter_value(Parameter.EMAIL_CONTRACT_END_REMINDER_CONTENT),
        )
    else:
        print(
            f"[task] send_email_member_contract_end_reminder: skipping email, because {member} has no active contract OR has a future contract"
        )


@shared_task
@transaction.atomic
def export_payment_parts_csv():
    due_date = datetime.today().replace(
        day=get_parameter_value(Parameter.PAYMENT_DUE_DAY)
    )
    existing_payments = get_existing_payments(due_date)
    payments = Payment.objects.bulk_create(generate_new_payments(due_date))
    payments.extend(existing_payments)

    payments.sort(key=lambda x: x.type)
    payments_grouped = {
        key: list(group)
        for key, group in itertools.groupby(payments, key=lambda x: x.type)
    }

    # export for product types
    for pt in get_active_product_types():
        export_product_or_coop_payment_csv(
            pt, payments_grouped[pt.name] if pt.name in payments_grouped else []
        )

    # export for coop shares
    export_product_or_coop_payment_csv(
        False,
        payments_grouped["Genossenschaftsanteile"]
        if "Genossenschaftsanteile" in payments_grouped
        else [],
    )


def export_product_or_coop_payment_csv(
    product_type: bool | ProductType, payments: list[Payment]
):
    KEY_NAME = "Name"
    KEY_IBAN = "IBAN"
    KEY_AMOUNT = "Betrag"
    KEY_VERWENDUNGSZWECK = "Verwendungszweck"
    KEY_MANDATE_REF = "Mandatsreferenz"
    KEY_MANDATE_DATE = "Mandatsdatum"

    output, writer = begin_csv_string(
        [
            KEY_NAME,
            KEY_IBAN,
            KEY_AMOUNT,
            KEY_VERWENDUNGSZWECK,
            KEY_MANDATE_REF,
            KEY_MANDATE_DATE,
        ]
    )

    for payment in payments:
        verwendungszweck = payment.mandate_ref.member.last_name + (
            " Geschäftsanteile" if not product_type else " " + product_type.name
        )

        writer.writerow(
            {
                KEY_NAME: f"{payment.mandate_ref.member.first_name} {payment.mandate_ref.member.last_name}",
                KEY_IBAN: payment.mandate_ref.member.iban,
                KEY_AMOUNT: payment.amount,
                KEY_VERWENDUNGSZWECK: verwendungszweck,
                KEY_MANDATE_REF: payment.mandate_ref.ref,
                KEY_MANDATE_DATE: format_date(payment.mandate_ref.member.sepa_consent),
            }
        )

    payment_type = product_type.name if product_type else "Geschäftsanteile"
    file = export_file(
        filename=(payment_type) + "-Einzahlungen",
        filetype=ExportedFile.FileType.CSV,
        content=bytes("".join(output.csv_string), "utf-8"),
        send_email=True,
    )
    transaction = PaymentTransaction.objects.create(file=file, type=payment_type)
    for p in payments:
        p.transaction = transaction
        p.save()


@shared_task
def generate_member_numbers():
    members = Member.objects.filter(member_no__isnull=True)
    today = date.today()
    for member in members:
        if member.coop_shares_quantity > 0 and member.coop_entry_date <= today:
            member.save()
            print(f"[task] generate_member_numbers: generated member_no for {member}")
