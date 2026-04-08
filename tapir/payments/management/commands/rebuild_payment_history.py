from django.core.management import BaseCommand
from django.db import transaction

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.tasks import (
    create_payments_for_this_month,
    export_payments_for_this_month,
)
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.models import Payment, PaymentTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class Command(BaseCommand):
    help = (
        "This deletes and rebuilds all payments related to contracts (Subscription and SolidarityContribution)."
        "It should be used with care. Maybe do a backup first?"
        "Use case: payment logic has changed (for example MonthlyPaymentBuilder changes) and payments from the old logic lead to wrong payments in the new logic."
        "Emails that would be sent when exporting payments are not sent when using this command"
    )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        answer = input(
            "Are you sure? Maybe do a backup before just in case :) [y/N] "
        ).lower()
        if answer not in ["y", "yes"]:
            print("Aborting")
            return

        Payment.objects.exclude(type=PAYMENT_TYPE_COOP_SHARES).delete()
        PaymentTransaction.objects.all().delete()

        current_date = get_parameter_value(
            key=ParameterKeys.PAYMENT_START_DATE
        ).replace(day=1)

        today = get_today()

        while current_date < today:
            create_payments_for_this_month(reference_date=current_date)
            export_payments_for_this_month(reference_date=current_date, send_mail=False)
            current_date = get_first_of_next_month(current_date)
