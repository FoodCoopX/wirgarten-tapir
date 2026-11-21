import csv
import datetime
import io
import locale
from decimal import Decimal
from typing import Iterable

from django.db import transaction

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.config import (
    ONE_OFF_TRANSACTION_TYPES,
    PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
    PAYMENT_TYPE_COOP_SHARES,
    get_payment_type_label,
)
from tapir.payments.services.pain_008_xml_file_creator import Pain008XmlFileCreator
from tapir.payments.services.payment_export_exclusion_period_service import (
    PaymentExportExclusionPeriodService,
)
from tapir.payments.services.payment_export_intended_use_builder import (
    PaymentExportIntendedUseBuilder,
)
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.models import (
    Payment,
    ExportedFile,
    PaymentTransaction,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.file_export import begin_csv_string, export_file
from tapir.wirgarten.templatetags.wirgarten import format_month_and_year
from tapir.wirgarten.utils import (
    format_date,
    format_currency,
    legal_status_is_cooperative,
)


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
        cls,
        reference_date: datetime.date,
        send_mail: bool,
        cache: dict,
        include_deposits: bool = True,
    ):
        contract_payments, coop_share_payments, deposit_payments = cls.split_payments(
            payments=cls.get_unexported_payments(reference_date=reference_date)
        )

        for payment in contract_payments:
            payment.excluded_from_export = (
                PaymentExportExclusionPeriodService.is_payment_excluded(
                    payment=payment, cache=cache
                )
            )
        exported_contract_payments = [
            payment for payment in contract_payments if not payment.excluded_from_export
        ]

        combined_contract_payments = cls.combine_contract_payments_by_mandate_ref(
            exported_contract_payments
        ).values()

        errors_failed_payments_contracts = cls.export_payments_if_necessary(
            combined_payments=combined_contract_payments,
            database_payments=contract_payments,
            payment_type="Verträge",
            reference_date=reference_date,
            send_mail=send_mail,
            cache=cache,
        )
        one_off_payment_groups = []
        if legal_status_is_cooperative(cache=cache):
            one_off_payment_groups.append(
                (PAYMENT_TYPE_COOP_SHARES, coop_share_payments)
            )
        if include_deposits and deposit_payments:
            one_off_payment_groups.append(
                (PAYMENT_TYPE_ASSOCIATION_DEPOSIT, deposit_payments)
            )
        errors = errors_failed_payments_contracts
        for payment_type, payments in one_off_payment_groups:
            errors.extend(
                cls.export_payments_if_necessary(
                    combined_payments=payments,
                    database_payments=payments,
                    payment_type=payment_type,
                    reference_date=reference_date,
                    send_mail=send_mail,
                    cache=cache,
                )
            )
        return errors

    @classmethod
    def export_payments_if_necessary(
        cls,
        combined_payments: Iterable[Payment],
        database_payments: Iterable[Payment],
        payment_type: str,
        reference_date: datetime.date,
        send_mail: bool,
        cache: dict,
    ):
        if not cls.should_export_payments(
            payment_type=payment_type, reference_date=reference_date
        ):
            return []

        csv_file, xml_file, errors_failed_payments = cls.create_csv_and_xml_files(
            payments=combined_payments,
            payment_type=payment_type,
            send_mail=send_mail,
            reference_date=reference_date,
            cache=cache,
        )
        cls.create_and_assign_transaction(
            csv_file=csv_file,
            xml_file=xml_file,
            payment_type=payment_type,
            payments=database_payments,
            reference_date=reference_date,
        )
        return errors_failed_payments

    @classmethod
    def should_export_payments(cls, payment_type: str, reference_date: datetime.date):
        last_transaction = (
            PaymentTransaction.objects.filter(
                type=payment_type, month__lte=reference_date
            )
            .order_by("created_at")
            .last()
        )
        return (
            last_transaction is None
            or reference_date.month != last_transaction.month.month
        )

    @classmethod
    def create_and_assign_transaction(
        cls,
        csv_file: ExportedFile,
        xml_file: ExportedFile | None,
        payment_type: str,
        payments: Iterable[Payment],
        reference_date: datetime.date,
    ):
        payment_transaction = PaymentTransaction.objects.create(
            csv_file=csv_file,
            xml_file=xml_file,
            type=payment_type,
            month=reference_date.replace(day=1),
        )
        for payment in payments:
            payment.transaction = payment_transaction
            payment.status = Payment.PaymentStatus.PAID
        Payment.objects.bulk_update(
            payments, ["transaction", "status", "excluded_from_export"]
        )

    @classmethod
    def combine_contract_payments_by_mandate_ref(cls, payments: list[Payment]):
        combined_payments: dict[str, Payment] = {}

        for payment in payments:
            if payment.mandate_ref.ref not in combined_payments:
                combined_payments[payment.mandate_ref.ref] = Payment(
                    mandate_ref=payment.mandate_ref,
                    amount=Decimal(0),
                    subscription_payment_range_start=payment.subscription_payment_range_start,
                    subscription_payment_range_end=payment.subscription_payment_range_end,
                )

            combined_payments[payment.mandate_ref.ref].amount += payment.amount
            combined_payments[
                payment.mandate_ref.ref
            ].subscription_payment_range_start = min(
                combined_payments[
                    payment.mandate_ref.ref
                ].subscription_payment_range_start,
                payment.subscription_payment_range_start,
            )
            combined_payments[
                payment.mandate_ref.ref
            ].subscription_payment_range_end = max(
                combined_payments[
                    payment.mandate_ref.ref
                ].subscription_payment_range_end,
                payment.subscription_payment_range_end,
            )
            combined_payments[payment.mandate_ref.ref].type += f", {payment.type}"

        combined_payments = {
            mandate_ref: payment
            for mandate_ref, payment in combined_payments.items()
            if payment.amount > 0
        }

        return combined_payments

    @classmethod
    def get_unexported_payments(cls, reference_date: datetime.date):
        max_due_date = get_last_day_of_month(reference_date)
        return (
            Payment.objects.filter(transaction__isnull=True, due_date__lte=max_due_date)
            .select_related("mandate_ref__member", "coop_share_transaction")
            .prefetch_related("coop_share_transaction__payments")
        )

    @classmethod
    def create_csv_and_xml_files(
        cls,
        payments: Iterable[Payment],
        payment_type: str,
        send_mail: bool,
        reference_date: datetime.date,
        cache: dict,
    ):
        file_name = f"{get_payment_type_label(payment_type)}-Einzahlungen {format_month_and_year(reference_date)}"
        payments = list(payments)
        csv_string = cls.build_csv_string(
            payments=payments,
            is_contract_payments=payment_type not in ONE_OFF_TRANSACTION_TYPES,
            cache=cache,
        )
        csv_file = export_file(
            filename=file_name,
            filetype=ExportedFile.FileType.CSV,
            content=bytes(csv_string, "utf-8"),
            send_email=send_mail
            and get_parameter_value(
                key=ParameterKeys.PAYMENT_SEND_CSV_FILE_PER_MAIL, cache=cache
            ),
            cache=cache,
        )
        xml_file = None
        errors_failed_payments = []
        if payments:
            xml_file, errors_failed_payments = (
                Pain008XmlFileCreator.create_xml_file_and_send_mail(
                    payments=payments,
                    file_name=file_name,
                    reference_date=reference_date,
                    send_mail=send_mail,
                    cache=cache,
                )
            )
        return csv_file, xml_file, errors_failed_payments

    @classmethod
    def build_csv_string(
        cls, payments: Iterable[Payment], is_contract_payments: bool, cache: dict
    ) -> str:
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
                payment=payment, is_contracts=is_contract_payments, cache=cache
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
        return file_content

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
    def split_payments(cls, payments: Iterable[Payment]):
        contract_payments = []
        coop_share_payments = []
        deposit_payments = []
        for payment in payments:
            if payment.type == PAYMENT_TYPE_COOP_SHARES:
                coop_share_payments.append(payment)
            elif payment.type == PAYMENT_TYPE_ASSOCIATION_DEPOSIT:
                deposit_payments.append(payment)
            else:
                contract_payments.append(payment)
        return contract_payments, coop_share_payments, deposit_payments
