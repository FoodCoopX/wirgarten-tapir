import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.tasks import (
    create_payments_for_this_month,
    export_payments_for_this_month,
)
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.models import PaymentTransaction, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class SubscriptionPaymentsRebuilder:
    @classmethod
    def rebuild_subscription_payments(cls, from_date: datetime.date, cache: dict):
        transactions = PaymentTransaction.objects.exclude(
            type=PAYMENT_TYPE_COOP_SHARES
        ).filter(
            month__gte=from_date.replace(day=1),
        )

        Payment.objects.filter(transaction__in=transactions).delete()
        transactions.delete()

        current_date = max(
            get_parameter_value(key=ParameterKeys.PAYMENT_START_DATE), from_date
        ).replace(day=1)
        today = get_today(cache=cache)

        while current_date < today:
            create_payments_for_this_month(reference_date=current_date)
            export_payments_for_this_month(reference_date=current_date, send_mail=False)
            current_date = get_first_of_next_month(current_date)
