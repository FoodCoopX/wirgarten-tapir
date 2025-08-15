import itertools
from collections import defaultdict

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    ExportedFile,
    Member,
    Product,
    ScheduledTask,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.service.file_export import begin_csv_string, export_file
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_active_subscriptions,
    get_active_and_future_subscriptions,
    get_product_price,
)
from tapir.wirgarten.utils import (
    format_subscription_list_html,
    get_now,
    get_today,
    legal_status_is_cooperative,
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


def _export_pick_list(product_type, include_equivalents=True, cache: dict = None):
    """
    Exports picklist or supplier list as CSV for a product type.
    include_equivalents: If true, the M-Äquivalent column is included -> Kommissionierliste, else Lieferantenliste
    """
    next_delivery_date = get_next_delivery_date(cache=cache)
    if not DeliveryCycleService.is_cycle_delivered_in_week(
        cycle=product_type.delivery_cycle, date=next_delivery_date, cache=cache
    ):
        print(
            f"Skipping export_pick_list_csv() for product type {product_type.name} because it is not due this week."
        )
        return

    KEY_PICKUP_LOCATION = "Abholort"
    KEY_M_EQUIVALENT = "M-Äquivalent"

    subscriptions = get_active_subscriptions(next_delivery_date, cache=cache).filter(
        product__type_id=product_type.id
    )
    grouped_subscriptions = defaultdict(list)

    for subscription in subscriptions:
        grouped_subscriptions[
            subscription.member.get_pickup_location(next_delivery_date).name
        ].append(subscription)

    variants = list(Product.objects.filter(type_id=product_type.id))
    variants.sort(key=lambda x: get_product_price(x, cache=cache).price)
    variant_names = [x.name for x in variants]

    header = [
        KEY_PICKUP_LOCATION,
        *variant_names,
    ]
    if include_equivalents:
        header.append(KEY_M_EQUIVALENT)
    output, writer = begin_csv_string(header)

    base_price = get_product_price(
        Product.objects.filter(type_id=product_type.id, base=True).first(), cache=cache
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
            (
                ParameterKeys.PICKING_SEND_ADMIN_EMAIL
                if include_equivalents
                else ParameterKeys.SUPPLIER_LIST_SEND_ADMIN_EMAIL
            ),
            cache=cache,
        ),
    )


def should_export_list_today(cache: dict):
    weekday_limit = get_parameter_value(
        ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL, cache=cache
    )
    today = get_today(cache=cache)

    # if the limit is wednesdays, export on thursday morning
    return today.weekday() == (weekday_limit + 1) % 7


@shared_task
def export_pick_list_csv():
    """
    Exports a CSV file containing the pick list for the next delivery.
    """
    cache = {}
    if not should_export_list_today(cache=cache):
        return

    all_product_types = {pt.name: pt for pt in get_active_product_types(cache=cache)}
    include_product_types = get_parameter_value(
        ParameterKeys.PICKING_PRODUCT_TYPES, cache=cache
    ).split(",")

    for type_name in include_product_types:
        type_name = type_name.strip()
        if type_name not in all_product_types:
            print(
                f"""export_pick_list_csv(): Ignoring unknown product type value in parameter '{ParameterKeys.PICKING_PRODUCT_TYPES}': {type_name}. Possible values: {all_product_types.keys}"""
            )
            continue
        _export_pick_list(all_product_types[type_name], True, cache=cache)


@shared_task
def export_supplier_list_csv():
    """
    Sums the quantity of product variants exports a list as CSV per product type.
    """
    cache = {}
    if not should_export_list_today(cache=cache):
        return

    all_product_types = {pt.name: pt for pt in get_active_product_types(cache=cache)}
    include_product_types = get_parameter_value(
        ParameterKeys.SUPPLIER_LIST_PRODUCT_TYPES, cache=cache
    ).split(",")

    for type_name in include_product_types:
        type_name = type_name.strip()
        if type_name not in all_product_types:
            print(
                f"""export_supplier_list_csv(): Ignoring unknown product type value in parameter '{ParameterKeys.SUPPLIER_LIST_PRODUCT_TYPES}': {type_name}. Possible values: {all_product_types.keys}"""
            )
            continue
        _export_pick_list(all_product_types[type_name], False, cache=cache)


def send_email_member_contract_end_reminder(member_id: str):
    member = Member.objects.get(pk=member_id)
    cache = {}
    today = get_today(cache=cache)
    next_month = today + relativedelta(months=1)
    active_subs = get_active_subscriptions(cache=cache).filter(member=member)
    if (
        active_subs.filter(end_date__lte=next_month).exists()
        and not get_active_and_future_subscriptions(cache=cache)
        .filter(member=member, start_date__gt=today)
        .exists()
    ):
        contract_list = format_subscription_list_html(active_subs)

        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=Events.FINAL_PICKUP,
                recipient_id_in_base_queryset=member.id,
                token_data={"contract_list": contract_list},
            ),
        )
    else:
        print(
            f"[task] send_email_member_contract_end_reminder: skipping email, because {member} has no active contract OR has a future contract"
        )


@shared_task
def generate_member_numbers(print_results=True, cache: dict = None):
    if cache is None:
        cache = {}
    members = Member.objects.filter(member_no__isnull=True)
    today = get_today(cache=cache)
    members_to_update = []
    next_member_number = Member.generate_member_no()
    for member in members:
        if legal_status_is_cooperative(cache=cache):
            coop_entry_date = member.coop_entry_date
            if coop_entry_date is None or coop_entry_date > today:
                continue

        member.member_no = next_member_number
        next_member_number = Member.generate_member_no(next_member_number)
        members_to_update.append(member)

    with transaction.atomic():
        Member.objects.bulk_update(members_to_update, ["member_no"])
        for member in members_to_update:
            TransactionalTrigger.fire_action(
                TransactionalTriggerData(
                    key=Events.MEMBERSHIP_ENTRY,
                    recipient_id_in_base_queryset=member.id,
                ),
            )
            if print_results:
                print(
                    f"[task] generate_member_numbers: generated member_no for {member}"
                )
