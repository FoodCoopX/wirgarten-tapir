import csv
import datetime
import io
import locale
from collections.abc import Iterable
from decimal import Decimal

from django.db import transaction

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.payment_export_intended_use_builder import (
    PaymentExportIntendedUseBuilder,
)
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.models import (
    Payment,
    ExportedFile,
    PaymentTransaction,
    MandateReference,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.file_export import begin_csv_string, export_file
from tapir.wirgarten.utils import format_date, format_currency


class PaymentExportBuilder:
    KEY_NAME = "Zahlungspflichtigen-Name"
    KEY_IBAN = "Zahlungspflichtigen-IBAN"
    KEY_AMOUNT = "Betrag"
    KEY_INTENDED_USE = "Verwendungszweck"
    KEY_MANDATE_REF = "Mandatsreferenz"
    KEY_MANDATE_DATE = "Mandatsdatum"

    @classmethod
    @transaction.atomic
    def export_all_unexported_payments(
        cls, reference_date: datetime.date, send_mail: bool, cache: dict
    ):
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
            send_mail=send_mail,
            cache=cache,
        )
        cls.export_payments_if_necessary(
            combined_payments=coop_share_payments,
            database_payments=coop_share_payments,
            is_contract_payments=False,
            reference_date=reference_date,
            send_mail=send_mail,
            cache=cache,
        )

    @classmethod
    def export_payments_if_necessary(
        cls,
        combined_payments: Iterable[Payment],
        database_payments: Iterable[Payment],
        is_contract_payments: bool,
        reference_date: datetime.date,
        send_mail: bool,
        cache: dict,
    ):
        if not cls.should_export_payments(
            is_contract_payments=is_contract_payments, reference_date=reference_date
        ):
            return

        exported_file = cls.export_payments(
            combined_payments,
            contract_payments=is_contract_payments,
            send_mail=send_mail,
            cache=cache,
        )

        cls.create_and_assign_transaction(
            file=exported_file,
            is_contract_payments=is_contract_payments,
            payments=database_payments,
            reference_date=reference_date,
        )

    @classmethod
    def should_export_payments(
        cls, is_contract_payments: bool, reference_date: datetime.date
    ):
        payment_type_display = (
            PaymentExportIntendedUseBuilder.get_payment_type_display_legacy(
                is_contract_payments
            )
        )
        last_transaction = (
            PaymentTransaction.objects.filter(
                type=payment_type_display, month__lte=reference_date
            )
            .order_by("created_at")
            .last()
        )
        if last_transaction is None:
            return True

        return reference_date.month != last_transaction.month.month

    @classmethod
    def create_and_assign_transaction(
        cls,
        file: ExportedFile,
        is_contract_payments: bool,
        payments: Iterable[Payment],
        reference_date: datetime.date,
    ):
        payment_transaction = PaymentTransaction.objects.create(
            file=file,
            type=PaymentExportIntendedUseBuilder.get_payment_type_display_legacy(
                is_contract_payments
            ),
            month=reference_date.replace(day=1),
        )
        for payment in payments:
            payment.transaction = payment_transaction
            payment.status = Payment.PaymentStatus.PAID
        Payment.objects.bulk_update(payments, ["transaction", "status"])

    @classmethod
    def combine_contract_payments_by_mandate_ref(cls, payments: list[Payment]):
        combined_payments: dict[MandateReference, Payment] = {}

        for payment in payments:
            if payment.mandate_ref not in combined_payments:
                combined_payments[payment.mandate_ref] = Payment(
                    mandate_ref=payment.mandate_ref,
                    amount=Decimal(0),
                    subscription_payment_range_start=payment.subscription_payment_range_start,
                    subscription_payment_range_end=payment.subscription_payment_range_end,
                )
            combined_payments[payment.mandate_ref].amount += payment.amount
            combined_payments[payment.mandate_ref].subscription_payment_range_start = (
                min(
                    combined_payments[
                        payment.mandate_ref
                    ].subscription_payment_range_start,
                    payment.subscription_payment_range_start,
                )
            )
            combined_payments[payment.mandate_ref].subscription_payment_range_end = max(
                combined_payments[payment.mandate_ref].subscription_payment_range_end,
                payment.subscription_payment_range_end,
            )

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
        send_mail: bool,
        cache: dict,
    ):
        previous_locale = locale.getlocale()
        locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")

        output, writer = begin_csv_string(
            [
                cls.KEY_NAME,
                cls.KEY_IBAN,
                cls.KEY_INTENDED_USE,
                cls.KEY_AMOUNT,
                cls.KEY_MANDATE_REF,
                cls.KEY_MANDATE_DATE,
            ]
        )

        for payment in payments:
            intended_use = PaymentExportIntendedUseBuilder.build_intended_use(
                payment=payment, is_contracts=contract_payments, cache=cache
            )

            writer.writerow(
                {
                    cls.KEY_NAME: f"{payment.mandate_ref.member.first_name} {payment.mandate_ref.member.last_name}",
                    cls.KEY_IBAN: payment.mandate_ref.member.iban,
                    cls.KEY_AMOUNT: format_currency(payment.amount).replace(".", ""),
                    cls.KEY_INTENDED_USE: intended_use,
                    cls.KEY_MANDATE_REF: payment.mandate_ref.ref,
                    cls.KEY_MANDATE_DATE: format_date(
                        payment.mandate_ref.member.sepa_consent.date()
                    ),
                }
            )

        locale.setlocale(locale.LC_ALL, previous_locale)

        file_content = "".join(output.csv_string)
        file_content = cls.add_header(file_content, cache)

        return export_file(
            filename=f"{PaymentExportIntendedUseBuilder.get_payment_type_display_legacy(contract_payments)}-Einzahlungen",
            filetype=ExportedFile.FileType.CSV,
            content=bytes(file_content, "utf-8"),
            send_email=send_mail,
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
    def split_payments_by_contract_or_coop_shares(cls, payments: Iterable[Payment]):
        contract_payments = []
        coop_share_payments = []
        for payment in payments:
            if payment.type == PAYMENT_TYPE_COOP_SHARES:
                coop_share_payments.append(payment)
            else:
                contract_payments.append(payment)

        return contract_payments, coop_share_payments
