import datetime

from celery import shared_task

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.wirgarten.models import (
    Payment,
)
from tapir.wirgarten.utils import (
    get_today,
)


@shared_task
def create_payments_for_this_month(reference_date: datetime.date = None):
    cache = {}
    if reference_date is None:
        reference_date = get_today(cache=cache)
    payments = MonthPaymentBuilder.build_payments_for_month(
        reference_date=reference_date, cache=cache, generated_payments=set()
    )
    Payment.objects.bulk_create(payments)


@shared_task
def export_payments_for_this_month(
    reference_date: datetime.date = None, send_mail: bool = True
):
    cache = {}
    if reference_date is None:
        reference_date = get_today(cache=cache)

    PaymentExportBuilder.export_all_unexported_payments(
        reference_date=reference_date,
        send_mail=send_mail,
        cache=cache,
    )
