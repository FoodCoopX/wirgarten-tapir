from datetime import date

from dateutil.relativedelta import relativedelta
from nanoid import generate

from tapir.configuration.parameter import get_parameter_value
from tapir.core.models import ID_LENGTH
from tapir.wirgarten.models import MandateReference, Subscription, Member
from tapir.wirgarten.parameters import Parameter

MANDATE_REF_LENGTH = 35
MANDATE_REF_ALPHABET = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GENO_SUFFIX = "/GENO"
SUBS_SUFFIX = "/PROD"


def generate_mandate_ref(member_id: int | str, coop_shares: bool):
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


def get_active_subscriptions_grouped_by_product_type(member: Member) -> dict:
    """
    Get all active subscriptions for a member grouped by product types.

    :param member: the Member instance
    :return: a dict of product_type.name -> Subscription[]
    """

    subscriptions = {}
    for sub in Subscription.objects.filter(member=member):
        product_type = sub.product.type.name
        if product_type not in subscriptions:
            subscriptions[product_type] = []

        subscriptions[product_type].append(sub)

    return subscriptions
