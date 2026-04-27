import logging

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.deliveries.services.pick_list_builder import PickListBuilder
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    ExportedFile,
    Member,
    ScheduledTask,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.file_export import export_file
from tapir.wirgarten.service.get_next_delivery_date import get_next_delivery_date
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_active_subscriptions,
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import (
    format_subscription_list_html,
    get_now,
    get_today,
    format_currency,
)

logger = logging.getLogger(__name__)


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
    if not DeliveryCycleService.is_product_type_delivered_in_week(
        product_type=product_type, date=next_delivery_date, cache=cache
    ):
        print(
            f"Skipping export_pick_list_csv() for product type {product_type.name} because it is not due this week."
        )
        return

    cls_string = PickListBuilder.build_pick_list(
        product_type=product_type, delivery_date=next_delivery_date, cache=cache
    )

    export_file(
        filename=f"{'Kommissionierliste' if include_equivalents else 'Lieferantenliste'}_{product_type.name}",
        filetype=ExportedFile.FileType.CSV,
        content=bytes(cls_string, "utf-8"),
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
                f"""export_pick_list_csv(): Ignoring unknown product type value in parameter '{ParameterKeys.PICKING_PRODUCT_TYPES}': {type_name}. Possible values: {all_product_types.keys()}"""
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
                f"""export_supplier_list_csv(): Ignoring unknown product type value in parameter '{ParameterKeys.SUPPLIER_LIST_PRODUCT_TYPES}': {type_name}. Possible values: {all_product_types.keys()}"""
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


def _fire_membership_entry_trigger(member: Member, cache: dict):
    number_of_coop_shares = member.coop_shares_quantity
    price_of_a_share = get_parameter_value(
        key=ParameterKeys.COOP_SHARE_PRICE, cache=cache
    )
    TransactionalTrigger.fire_action(
        TransactionalTriggerData(
            key=Events.MEMBERSHIP_ENTRY,
            recipient_id_in_base_queryset=member.id,
            token_data={
                "number_of_coop_shares": number_of_coop_shares,
                "price_of_a_share": format_currency(price_of_a_share),
                "price_of_all_shares": format_currency(
                    number_of_coop_shares * price_of_a_share
                ),
            },
        ),
    )


@shared_task
def generate_member_numbers(cache: dict = None):
    """
    Assigns member numbers to members that don't have one yet.
    Handles members whose trial period has ended (when MEMBER_NUMBER_ONLY_AFTER_TRIAL
    is enabled) and catches any members that slipped through immediate assignment.
    Fires the MEMBERSHIP_ENTRY mail trigger on success.
    """
    if cache is None:
        cache = {}
    members = Member.objects.filter(member_no__isnull=True)

    with transaction.atomic():
        for member in members:
            if not MemberNumberService.assign_member_number_if_eligible(
                member, cache=cache
            ):
                continue

            _fire_membership_entry_trigger(member, cache)
            logger.info(f"generate_member_numbers: generated member_no for {member}")
