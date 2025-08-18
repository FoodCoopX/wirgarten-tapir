from celery import shared_task

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.wirgarten.models import (
    Payment,
)
from tapir.wirgarten.utils import (
    get_today,
)


@shared_task
def create_payments_for_this_month():
    cache = {}
    today = get_today(cache=cache)
    payments = MonthPaymentBuilder.build_payments_for_month(
        reference_date=today, cache=cache
    )
    Payment.objects.bulk_create(payments)
