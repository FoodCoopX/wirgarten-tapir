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

    # export_payments_for_this_month will usually export on the first day of the month
    # depending on when create_payments_for_this_month is run, for example if the server was down from the 31st at 23:00 to 1st at 08:00,
    # the payments may not be created yet. So we make sure that they are created before exporting.
    create_payments_for_this_month(reference_date)

    PaymentExportBuilder.export_all_unexported_payments(
        reference_date=reference_date,
        send_mail=send_mail,
        cache=cache,
    )
