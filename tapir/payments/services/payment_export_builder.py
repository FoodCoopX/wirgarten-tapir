import datetime
import itertools
from collections.abc import Iterable

from django.db import transaction

from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.models import Payment, ExportedFile, PaymentTransaction
from tapir.wirgarten.service.file_export import begin_csv_string, export_file
from tapir.wirgarten.utils import format_date


class PaymentExportBuilder:
    KEY_NAME = "Name"
    KEY_IBAN = "IBAN"
    KEY_AMOUNT = "Betrag"
    KEY_VERWENDUNGSZWECK = "Verwendungszweck"
    KEY_MANDATE_REF = "Mandatsreferenz"
    KEY_MANDATE_DATE = "Mandatsdatum"

    @classmethod
    @transaction.atomic
    def export_all_unexported_payments(cls, reference_date: datetime.date, cache: dict):
        payments = cls.get_unexported_payments(reference_date=reference_date)
        payments_grouped_by_type = cls.group_payments_by_type(payments)

        for payment_type, payments in payments_grouped_by_type.items():
            cls.export_payments_of_type(
                payment_type,
                payments,
                cache=cache,
            )

    @classmethod
    def get_unexported_payments(cls, reference_date: datetime.date):
        max_due_date = get_last_day_of_month(reference_date)
        return Payment.objects.filter(
            transaction__isnull=True, due_date__lte=max_due_date
        )

    @classmethod
    def group_payments_by_type(cls, payments: Iterable[Payment]):
        payments = sorted(payments, key=lambda payment: payment.type)
        payments_grouped_by_type = {
            payment_type: list(group)
            for payment_type, group in itertools.groupby(
                payments, key=lambda payment: payment.type
            )
        }
        return payments_grouped_by_type

    @classmethod
    def export_payments_of_type(
        cls, payment_type: str, payments: list[Payment], cache: dict
    ):
        output, writer = begin_csv_string(
            [
                cls.KEY_NAME,
                cls.KEY_IBAN,
                cls.KEY_AMOUNT,
                cls.KEY_VERWENDUNGSZWECK,
                cls.KEY_MANDATE_REF,
                cls.KEY_MANDATE_DATE,
            ]
        )

        for payment in payments:
            verwendungszweck = f"{payment.mandate_ref.member.last_name} {payment_type}"

            writer.writerow(
                {
                    cls.KEY_NAME: f"{payment.mandate_ref.member.first_name} {payment.mandate_ref.member.last_name}",
                    cls.KEY_IBAN: payment.mandate_ref.member.iban,
                    cls.KEY_AMOUNT: payment.amount,
                    cls.KEY_VERWENDUNGSZWECK: verwendungszweck,
                    cls.KEY_MANDATE_REF: payment.mandate_ref.ref,
                    cls.KEY_MANDATE_DATE: format_date(
                        payment.mandate_ref.member.sepa_consent
                    ),
                }
            )

        payment_type_display = payment_type
        if (
            payment_type_display
            == MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION
        ):
            payment_type_display = "Solidarbeitrag"
        file = export_file(
            filename=f"{payment_type_display}-Einzahlungen",
            filetype=ExportedFile.FileType.CSV,
            content=bytes("".join(output.csv_string), "utf-8"),
            send_email=True,
            cache=cache,
        )
        payment_transaction = PaymentTransaction.objects.create(
            file=file, type=payment_type_display
        )
        for payment in payments:
            payment.transaction = payment_transaction
        Payment.objects.bulk_update(payments, ["transaction"])
