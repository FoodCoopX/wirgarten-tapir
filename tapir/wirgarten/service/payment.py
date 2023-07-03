import itertools
from collections import OrderedDict
from datetime import date

from dateutil.relativedelta import relativedelta
from nanoid import generate

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Subscription, Member, Payment
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_product_price,
    get_future_subscriptions,
)

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
    prefix = f"{member.last_name[:5]}{member.first_name[:5]}/".upper()

    return f"""{prefix}{generate(MANDATE_REF_ALPHABET, MANDATE_REF_LENGTH - len(prefix))}"""


def get_next_payment_date(reference_date: date = date.today()):
    """
    Get the next date on which payments are due.

    :param reference_date: start at this date, default: today()
    :return: the next payment due date
    """

    due_day = get_parameter_value(Parameter.PAYMENT_DUE_DAY)

    if reference_date.day < due_day:
        next_payment = reference_date.replace(day=due_day)
    else:
        next_payment = reference_date.replace(day=due_day) + relativedelta(months=1)
    return next_payment


def generate_new_payments(due_date: date) -> list[Payment]:
    """
    Generates payments for the given due date. If a payment for this date and mandate_ref is already persisted, it will be skipped.
    The generated payments are not persisted!

    :param due_date: The date on which the payment will be due.
    :return: the list of new Payments
    """

    payments = []

    for (mandate_ref, product_type), subs in itertools.groupby(
        iterable=Subscription.objects.filter(
            start_date__lte=due_date, end_date__gte=due_date
        ).order_by("mandate_ref", "product__type"),
        key=lambda x: (x.mandate_ref, x.product.type.name),
    ):
        if not Payment.objects.filter(
            mandate_ref=mandate_ref, due_date=due_date, type=product_type
        ).exists():
            amount = float(
                round(
                    sum(
                        map(
                            lambda x: x.total_price,
                            subs,
                        )
                    ),
                    2,
                )
            )

            payments.append(
                Payment(
                    due_date=due_date,
                    amount=amount,
                    mandate_ref=mandate_ref,
                    status=Payment.PaymentStatus.DUE,
                    type=product_type,
                )
            )

    return payments


def get_active_subscriptions_grouped_by_product_type(
    member: Member, reference_date: date = date.today()
) -> dict:
    """
    Get all active subscriptions for a member grouped by product types.

    :param member: the Member instance
    :return: a dict of product_type.name -> Subscription[]
    """

    subscriptions = OrderedDict()
    for sub in get_active_subscriptions(reference_date).filter(member=member):
        product_type = sub.product.type.name
        if product_type not in subscriptions:
            subscriptions[product_type] = []

        subscriptions[product_type].append(sub)

    return subscriptions


def get_existing_payments(due_date: date) -> list[Payment]:
    """
    Gets already persisted payments for the given due date

    :param due_date: the date on which the payments are due
    :return: the list of persisted payments for the given date
    """

    return list(
        Payment.objects.filter(transaction__isnull=True, due_date=due_date)
    )


def get_total_payment_amount(due_date: date) -> list[Payment]:
    """
    Returns the total € amount for all due payments on this date.

    :param due_date: the date on which the payments are due
    :return: the list of existing and projected payments for the given date
    """
    payments = generate_new_payments(due_date)
    payments.extend(get_existing_payments(due_date))
    return sum(map(lambda x: float(x.amount), payments))


def get_solidarity_overplus(reference_date: date = date.today()) -> float:
    """
    Returns the total solidarity price sum for the active subscriptions during the reference date.

    :param reference_date: the date for which the subscription is active
    :return: the total solidarity overplus amount
    """

    return sum(
        map(
            lambda sub: sub["quantity"]
            * sub["solidarity_price"]
            * float(get_product_price(sub["product"]).price),
            get_future_subscriptions(reference_date).values(
                "quantity", "product", "solidarity_price"
            ),
        )
    )
