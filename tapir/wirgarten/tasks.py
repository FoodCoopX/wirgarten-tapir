import itertools
from collections import defaultdict

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import EVEN_WEEKS, ODD_WEEKS, WEEKLY
from tapir.wirgarten.models import (
    ExportedFile,
    Member,
    Payment,
    PaymentTransaction,
    Product,
    ProductType,
    ScheduledTask,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.service.email import send_email
from tapir.wirgarten.service.file_export import begin_csv_string, export_file
from tapir.wirgarten.service.payment import generate_new_payments, get_existing_payments
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_active_subscriptions,
    get_future_subscriptions,
    get_product_price,
)
from tapir.wirgarten.tapirmail import Events
from tapir.wirgarten.utils import (
    format_date,
    format_subscription_list_html,
    get_now,
    get_today,
)


@shared_task
def execute_scheduled_tasks():
    """
    Executes all scheduled tasks that are due.
    """

    scheduled_tasks = ScheduledTask.objects.filter(
        eta__lte=get_now(), status=ScheduledTask.STATUS_PENDING
    )
    for scheduled_task in scheduled_tasks:
        print("Executing scheduled task: ", scheduled_task)
        scheduled_task.execute()


def _export_pick_list(product_type, include_equivalents=True):
    """
    Exports picklist or supplier list as CSV for a product type.
    indclude_equivalents: If true, the M-Äquivalent column is included -> Kommissionierliste, else Lieferantenliste
    """
    next_delivery_date = get_next_delivery_date()
    if product_type.delivery_cycle != WEEKLY[0]:
        _, week, _ = next_delivery_date.isocalendar()
        is_even_week = week % 2 == 0

        # DEBUG LOG
        print(
            product_type.name,
            next_delivery_date,
            product_type.delivery_cycle,
            is_even_week,
            (product_type.delivery_cycle == EVEN_WEEKS[0] and not is_even_week)
            or (product_type.delivery_cycle == ODD_WEEKS[0] and is_even_week),
        )

        if (product_type.delivery_cycle == EVEN_WEEKS[0] and not is_even_week) or (
            product_type.delivery_cycle == ODD_WEEKS[0] and is_even_week
        ):
            print(
                f"Skipping export_pick_list_csv() for product type {product_type.name} because it is not due this week."
            )
            return

    KEY_PICKUP_LOCATION = "Abholort"
    KEY_M_EQUIVALENT = "M-Äquivalent"

    subscriptions = get_active_subscriptions(next_delivery_date).filter(
        product__type_id=product_type.id
    )
    grouped_subscriptions = defaultdict(list)

    for subscription in subscriptions:
        grouped_subscriptions[
            subscription.member.get_pickup_location(next_delivery_date).name
        ].append(subscription)

    variants = list(Product.objects.filter(type_id=product_type.id))
    variants.sort(key=lambda x: get_product_price(x).price)
    variant_names = [x.name for x in variants]

    header = [
        KEY_PICKUP_LOCATION,
        *variant_names,
    ]
    if include_equivalents:
        header.append(KEY_M_EQUIVALENT)
    output, writer = begin_csv_string(header)

    base_price = get_product_price(
        Product.objects.filter(type_id=product_type.id, base=True).first()
    ).price

    for pickup_location, subs in sorted(
        grouped_subscriptions.items(), key=lambda x: x[0]
    ):
        subs.sort(key=lambda x: x.product.name)
        grouped_subs = {
            key: sum([x.quantity for x in group])
            for key, group in itertools.groupby(subs, key=lambda sub: sub.product.name)
        }

        sum_without_soli = sum(map(lambda x: x.total_price_without_soli, subs))

        data = {
            KEY_PICKUP_LOCATION: pickup_location,
            **grouped_subs,
        }
        if include_equivalents:
            data[KEY_M_EQUIVALENT] = round(sum_without_soli / base_price, 2)
        writer.writerow(data)

    export_file(
        filename=f"{'Kommissionierliste' if include_equivalents else 'Lieferantenliste'}_{product_type.name}",
        filetype=ExportedFile.FileType.CSV,
        content=bytes("".join(output.csv_string), "utf-8"),
        send_email=get_parameter_value(
            Parameter.PICK_LIST_SEND_ADMIN_EMAIL
            if include_equivalents
            else Parameter.SUPPLIER_LIST_SEND_ADMIN_EMAIL
        ),
    )


@shared_task
def export_pick_list_csv():
    """
    Exports a CSV file containing the pick list for the next delivery.
    """
    all_product_types = {pt.name: pt for pt in get_active_product_types()}
    include_product_types = get_parameter_value(
        Parameter.PICK_LIST_PRODUCT_TYPES
    ).split(",")

    for type_name in include_product_types:
        type_name = type_name.strip()
        if type_name not in all_product_types:
            print(
                f"""export_pick_list_csv(): Ignoring unknown product type value in parameter '{Parameter.PICK_LIST_PRODUCT_TYPES}': {type_name}. Possible values: {all_product_types.keys}"""
            )
            continue
        _export_pick_list(all_product_types[type_name], True)


@shared_task
def export_supplier_list_csv():
    """
    Sums the quantity of product variants exports a list as CSV per product type.
    """
    all_product_types = {pt.name: pt for pt in get_active_product_types()}
    include_product_types = get_parameter_value(
        Parameter.SUPPLIER_LIST_PRODUCT_TYPES
    ).split(",")

    for type_name in include_product_types:
        type_name = type_name.strip()
        if type_name not in all_product_types:
            print(
                f"""export_supplier_list_csv(): Ignoring unknown product type value in parameter '{Parameter.SUPPLIER_LIST_PRODUCT_TYPES}': {type_name}. Possible values: {all_product_types.keys}"""
            )
            continue
        _export_pick_list(all_product_types[type_name], False)


def send_email_member_contract_end_reminder(member_id: str):
    member = Member.objects.get(pk=member_id)

    today = get_today()
    next_month = today + relativedelta(months=1)
    active_subs = get_active_subscriptions().filter(member=member)
    if (
        active_subs.filter(end_date__lte=next_month).exists()
        and not get_future_subscriptions()
        .filter(member=member, start_date__gt=today)
        .exists()
    ):
        contract_list = format_subscription_list_html(active_subs)
        send_email(
            to_email=[member.email],
            subject=get_parameter_value(Parameter.EMAIL_CONTRACT_END_REMINDER_SUBJECT),
            content=get_parameter_value(Parameter.EMAIL_CONTRACT_END_REMINDER_CONTENT),
            variables={"contract_list": contract_list},
        )

        TransactionalTrigger.fire_action(
            Events.FINAL_PICKUP, member.email, {"contract_list": contract_list}
        )
    else:
        print(
            f"[task] send_email_member_contract_end_reminder: skipping email, because {member} has no active contract OR has a future contract"
        )


@shared_task
@transaction.atomic
def export_payment_parts_csv(reference_date=None):
    if reference_date is None:
        reference_date = get_today()

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
                    KEY_MANDATE_DATE: format_date(
                        payment.mandate_ref.member.sepa_consent
                    ),
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

    due_date = reference_date.replace(
        day=get_parameter_value(Parameter.PAYMENT_DUE_DAY)
    )

    print(
        f"[task] export_payment_parts_csv: generating payments for due date {format_date(due_date)}"
    )

    payments = generate_new_payments(due_date)
    for p in payments:
        if p.id is None:
            p.save()

    payments.sort(key=lambda x: x.type if x.type else "")
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
    coop_share_payments = Payment.objects.filter(
        transaction__isnull=True, due_date__lte=due_date, type="Genossenschaftsanteile"
    )
    export_product_or_coop_payment_csv(
        False,
        coop_share_payments,
    )


@shared_task
def generate_member_numbers():
    members = Member.objects.filter(member_no__isnull=True)
    today = get_today()
    for member in members:
        with transaction.atomic():
            if member.coop_shares_quantity > 0 and member.coop_entry_date <= today:
                member.member_no = member.generate_member_no()
                member.save()

                TransactionalTrigger.fire_action(Events.MEMBERSHIP_ENTRY, member.email)

                print(
                    f"[task] generate_member_numbers: generated member_no for {member}"
                )
