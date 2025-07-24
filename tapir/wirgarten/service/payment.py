from collections import OrderedDict
from datetime import date
from decimal import Decimal
from typing import Dict

from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from nanoid import generate
from unidecode import unidecode

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, Payment, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import get_today

MANDATE_REF_LENGTH = 35
MANDATE_REF_ALPHABET = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def generate_mandate_ref(member_id: str):
    """
    Generates a new mandate reference string.

    UUUUUUUUUU/XXXXXXXXXXXXXXXXXXXXXXXX

    U = User Name
    X = Random String

    :param member_id: the ID of the TapirUser/Member
    :return: the mandate reference string
    """

    member = Member.objects.get(id=member_id)
    cleaned_name = unidecode(f"{member.last_name[:5]}{member.first_name[:5]}")
    prefix = f"{cleaned_name}/".upper()

    return f"""{prefix}{generate(MANDATE_REF_ALPHABET, MANDATE_REF_LENGTH - len(prefix))}"""


def get_next_payment_date(reference_date: date = None, cache: Dict = None):
    """
    Get the next date on which payments are due.

    :return: the next payment due date
    """
    if reference_date is None:
        reference_date = get_today(cache=cache)

    due_day = get_parameter_value(ParameterKeys.PAYMENT_DUE_DAY, cache=cache)

    if reference_date.day < due_day:
        next_payment = reference_date.replace(day=due_day)
    else:
        next_payment = reference_date.replace(day=due_day) + relativedelta(months=1)
    return next_payment


def generate_new_payments(due_date: date, cache: Dict) -> list[Payment]:
    """
    Generates payments for the given due date. The generated payments are not persisted!

    :return: the list of new Payments
    """
    payments = []

    subscriptions = Subscription.objects.filter(
        start_date__lte=due_date, end_date__gte=due_date
    ).order_by("mandate_ref", "product__type")

    grouped = {}
    for sub in subscriptions:
        key = (sub.mandate_ref, sub.product.type)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(sub)

    for (mandate_ref, product_type), subs in grouped.items():
        existing = Payment.objects.filter(
            mandate_ref=mandate_ref, due_date=due_date, type=product_type.name
        )
        if not existing.exists():
            amount = sum(sub.total_price(cache=cache) for sub in subs)

            payments.append(
                Payment(
                    due_date=due_date,
                    amount=Decimal(amount).quantize(Decimal("0.01")),
                    mandate_ref=mandate_ref,
                    status=Payment.PaymentStatus.DUE,
                    type=product_type.name,
                )
            )
        else:
            payments.extend(existing)

    return payments


def get_active_subscriptions_grouped_by_product_type(
    member: Member,
    reference_date: date = None,
    include_future_subscriptions: bool = False,
    cache: Dict = None,
) -> OrderedDict[str, list[Subscription]]:
    """
    Get all active subscriptions for a member grouped by product types.

    :param member: the Member instance
    :return: a dict of product_type.name -> Subscription[]
    """
    if reference_date is None:
        reference_date = get_today(cache=cache)

    subscriptions_by_product_type = OrderedDict(
        {
            p.name: []
            for p in TapirCache.get_product_types_in_standard_order(cache=cache)
        }
    )

    subscriptions = (
        get_active_and_future_subscriptions(reference_date, cache=cache)
        if include_future_subscriptions
        else get_active_subscriptions(reference_date, cache=cache)
    )

    for sub in subscriptions.filter(member=member).select_related("product__type"):
        product_type = sub.product.type.name
        subscriptions_by_product_type[product_type].append(sub)

    return subscriptions_by_product_type


def get_total_payment_amount(due_date: date, cache: dict) -> list[Payment]:
    """
    Returns the total € amount for all due payments on this date.

    :param due_date: the date on which the payments are due
    :return: the list of existing and projected payments for the given date
    """

    total_amount = 0.0

    subscriptions = (
        Subscription.objects.filter(start_date__lte=due_date, end_date__gte=due_date)
        .order_by("mandate_ref", "product__type")
        .select_related("mandate_ref", "product__type")
    )

    existing_payments = {
        f"{p.mandate_ref.ref}-{p.type}": float(p.amount)
        for p in Payment.objects.filter(due_date=due_date)
    }
    for sub in subscriptions:
        total_amount += existing_payments.get(
            f"{sub.mandate_ref.ref}-{sub.product.type.name}", None
        ) or sub.total_price(due_date, cache=cache)

    total_amount += float(
        Payment.objects.filter(
            type="Genossenschaftsanteile", due_date=due_date
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0.0
    )
    return total_amount
