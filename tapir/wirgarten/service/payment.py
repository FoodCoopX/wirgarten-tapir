import itertools
from collections import OrderedDict
from datetime import date

from dateutil.relativedelta import relativedelta
from nanoid import generate

from tapir.configuration.parameter import get_parameter_value
from tapir.core.models import ID_LENGTH
from tapir.wirgarten.models import MandateReference, Subscription, Member, Payment
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_product_price,
    get_future_subscriptions,
)

MANDATE_REF_LENGTH = 35
MANDATE_REF_ALPHABET = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GENO_SUFFIX = "/GENO"
SUBS_SUFFIX = "/PROD"


def generate_mandate_ref(member_id: str, coop_shares: bool):
    """
    Generates a new mandate reference string.

    UUUUUUUUUU/XXXXXXXXXXXXXXXXXXX/TTTT

    U = User ID
    X = Random String
    T = Payment Type (Coop Shares: GENO, Subscriptions: PROD)

    :param member_id: the ID of the TapirUser/Member
    :param coop_shares: if True, the mandate ref will be generated for coop shares, else for subscriptions
    :return: the mandate reference string
    """

    prefix = f"""{str(member_id).zfill(ID_LENGTH)}/"""

    def __generate_ref(suffix):
        return f"""{generate(MANDATE_REF_ALPHABET, MANDATE_REF_LENGTH - len(prefix) - len(suffix))}{suffix}"""

    return f"""{prefix}{__generate_ref(GENO_SUFFIX if coop_shares else SUBS_SUFFIX)}"""


def is_mandate_ref_for_coop_shares(mandate_ref: str | MandateReference):
    """
    Checks if a mandate reference is for coop shares or for subscriptions.

    :param mandate_ref: the mandate reference string
    :return: True, if the mandate ref is for coop shares
    """

    if type(mandate_ref) == MandateReference:
        mandate_ref = mandate_ref.ref

    return mandate_ref.endswith(GENO_SUFFIX)


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


def generate_new_payments(due_date: date) -> [Payment]:
    """
    Generates payments for the given due date. If a payment for this date and mandate_ref is already persisted, it will be skipped.
    The generated payments are not persisted!

    :param due_date: The date on which the payment will be due.
    :return: the list of new Payments
    """

    payments = []

    for mandate_ref, subs in itertools.groupby(
        iterable=Subscription.objects.filter(
            start_date__lte=due_date, end_date__gte=due_date
        ).order_by("mandate_ref"),
        key=lambda x: x.mandate_ref,
    ):
        if not Payment.objects.filter(
            mandate_ref=mandate_ref, due_date=due_date
        ).exists():
            amount = float(
                round(
                    sum(
                        map(
                            lambda x: x.get_total_price(),
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
                )
            )

    return payments


def get_active_subscriptions_grouped_by_product_type(
    member: Member, reference_date=date.today()
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


def get_existing_payments(due_date: date) -> [Payment]:
    """
    Gets already persisted payments for the given due date

    :param due_date: the date on which the payments are due
    :return: the list of persisted payments for the given date
    """

    return list(
        Payment.objects.filter(transaction__isnull=True, due_date__lte=due_date)
    )


def get_total_payment_amount(due_date: date) -> [Payment]:
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
