import csv
import datetime
import io
import locale
from collections.abc import Iterable
from decimal import Decimal

from django.db import transaction

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.models import (
    Payment,
    ExportedFile,
    PaymentTransaction,
    MandateReference,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.file_export import begin_csv_string, export_file
from tapir.wirgarten.utils import format_date, get_now, format_currency


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
        contract_payments, coop_share_payments = (
            cls.split_payments_by_contract_or_coop_shares(payments)
        )

        combined_contract_payments = cls.combine_contract_payments_by_mandate_ref(
            contract_payments
        )

        cls.export_payments_if_necessary(
            combined_payments=combined_contract_payments,
            database_payments=contract_payments,
            is_contract_payments=True,
            reference_date=reference_date,
            cache=cache,
        )
        cls.export_payments_if_necessary(
            combined_payments=coop_share_payments,
            database_payments=coop_share_payments,
            is_contract_payments=False,
            reference_date=reference_date,
            cache=cache,
        )

    @classmethod
    def export_payments_if_necessary(
        cls,
        combined_payments: Iterable[Payment],
        database_payments: Iterable[Payment],
        is_contract_payments: bool,
        reference_date: datetime.date,
        cache: dict,
    ):
        if not cls.should_export_payments(
            is_contract_payments=is_contract_payments, reference_date=reference_date
        ):
            return

        exported_file = cls.export_payments(
            combined_payments,
            contract_payments=is_contract_payments,
            cache=cache,
        )
        cls.create_and_assign_transaction(
            file=exported_file,
            is_contract_payments=is_contract_payments,
            payments=database_payments,
            reference_date=reference_date,
            cache=cache,
        )

    @classmethod
    def should_export_payments(
        cls, is_contract_payments: bool, reference_date: datetime.date
    ):
        payment_type_display = cls.get_payment_type_display(is_contract_payments)
        last_transaction = (
            PaymentTransaction.objects.filter(
                type=payment_type_display, created_at__lte=reference_date
            )
            .order_by("created_at")
            .last()
        )
        if last_transaction is None:
            return True

        return reference_date.month != last_transaction.created_at.month

    @classmethod
    def create_and_assign_transaction(
        cls,
        file: ExportedFile,
        is_contract_payments: bool,
        payments: Iterable[Payment],
        reference_date: datetime.date,
        cache: dict,
    ):
        created_at = datetime.datetime.combine(
            reference_date,
            get_now(cache=cache).time(),
            tzinfo=get_now(cache=cache).tzinfo,
        )
        payment_transaction = PaymentTransaction.objects.create(
            file=file,
            type=cls.get_payment_type_display(is_contract_payments),
            created_at=created_at,
        )
        for payment in payments:
            payment.transaction = payment_transaction
            payment.status = Payment.PaymentStatus.PAID
        Payment.objects.bulk_update(payments, ["transaction", "status"])

    @classmethod
    def combine_contract_payments_by_mandate_ref(cls, payments: list[Payment]):
        combined_payments: dict[MandateReference, Payment] = {}

        for payment in payments:
            if payment.mandate_ref not in combined_payments.keys():
                combined_payments[payment.mandate_ref] = Payment(
                    mandate_ref=payment.mandate_ref,
                    amount=Decimal(0),
                )
            combined_payments[payment.mandate_ref].amount += payment.amount

        return combined_payments.values()

    @classmethod
    def get_unexported_payments(cls, reference_date: datetime.date):
        max_due_date = get_last_day_of_month(reference_date)
        return Payment.objects.filter(
            transaction__isnull=True, due_date__lte=max_due_date
        )

    @classmethod
    def export_payments(
        cls,
        payments: Iterable[Payment],
        contract_payments: bool,
        cache: dict,
    ):
        previous_locale = locale.getlocale()
        locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")

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

        payment_type_display = cls.get_payment_type_display(contract_payments)

        for payment in payments:
            verwendungszweck = f"{get_parameter_value(key=ParameterKeys.SITE_NAME)}, {payment.mandate_ref.member.last_name}, {payment_type_display}"

            writer.writerow(
                {
                    cls.KEY_NAME: f"{payment.mandate_ref.member.first_name} {payment.mandate_ref.member.last_name}",
                    cls.KEY_IBAN: payment.mandate_ref.member.iban,
                    cls.KEY_AMOUNT: format_currency(payment.amount).replace(".", ""),
                    cls.KEY_VERWENDUNGSZWECK: verwendungszweck,
                    cls.KEY_MANDATE_REF: payment.mandate_ref.ref,
                    cls.KEY_MANDATE_DATE: format_date(
                        payment.mandate_ref.member.sepa_consent.date()
                    ),
                }
            )

        locale.setlocale(locale.LC_ALL, previous_locale)

        file_content = "".join(output.csv_string)
        if get_parameter_value(ParameterKeys.PAYMENT_EXPORT_WITH_HEADER, cache=cache):
            file_content = cls.add_header(file_content, cache)

        return export_file(
            filename=f"{payment_type_display}-Einzahlungen",
            filetype=ExportedFile.FileType.CSV,
            content=bytes(file_content, "utf-8"),
            send_email=True,
            cache=cache,
        )

    @classmethod
    def add_header(cls, file_content: str, cache: dict):
        organisation_name = get_parameter_value(
            key=ParameterKeys.SITE_NAME, cache=cache
        )
        iban = get_parameter_value(
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN, cache=cache
        )
        credential_identifier = get_parameter_value(
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER, cache=cache
        )

        header = io.StringIO()
        writer = csv.writer(header, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writerow(["Basis-Lastschriften"])
        writer.writerow([organisation_name, iban, credential_identifier])

        return "".join([header.getvalue(), file_content])

    @classmethod
    def get_payment_type_display(cls, contract_payments: bool):
        return "Verträge" if contract_payments else PAYMENT_TYPE_COOP_SHARES

    @classmethod
    def split_payments_by_contract_or_coop_shares(cls, payments: Iterable[Payment]):
        contract_payments = []
        coop_share_payments = []
        for payment in payments:
            if payment.type == PAYMENT_TYPE_COOP_SHARES:
                coop_share_payments.append(payment)
            else:
                contract_payments.append(payment)

        return contract_payments, coop_share_payments
