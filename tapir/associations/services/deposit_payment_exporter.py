from django.db import transaction

from tapir.associations.models import AssociationDeposit
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.pain_008_xml_string_generator import (
    Pain008XmlStringGenerator,
    Pain008XmlSinglePaymentException,
    Pain008XmlGlobalException,
)
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.models import Payment, PaymentTransaction, ExportedFile
from tapir.wirgarten.service.file_export import export_file, send_exported_file
from tapir.wirgarten.utils import get_today
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class DepositPaymentExporter:
    @classmethod
    @transaction.atomic
    def export(cls, reference_date, send_mail, cache):
        from tapir.payments.services.payment_export_builder import PaymentExportBuilder

        pending = Payment.objects.filter(
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
            due_date__lte=get_last_day_of_month(reference_date),
        )
        locked_deposits = list(
            AssociationDeposit.objects.select_for_update()
            .filter(pk__in=pending.values("association_deposit_id"))
            .order_by("pk")
        )
        payments = list(
            pending.filter(association_deposit__in=locked_deposits)
            .select_for_update(of=("self",))
            .select_related("mandate_ref__member")
        )
        if not payments:
            return []
        collection_date = CoopSharePurchaseHandler.get_payment_due_date(
            max(reference_date, get_today(cache)), cache
        )
        valid = []
        errors = []
        try:
            for payment in payments:
                try:
                    Pain008XmlStringGenerator.validate_single_payment(
                        payment, cache, collection_date
                    )
                    valid.append(payment)
                except Pain008XmlSinglePaymentException as error:
                    errors.append(error.message)
            if not valid:
                return errors
            xml = Pain008XmlStringGenerator.build_xml_string(
                valid, cache, collection_date
            )
        except Pain008XmlGlobalException as error:
            return errors + [error.message]

        name = f"Vereinseinlagen-Einzahlungen {reference_date:%Y-%m}"
        csv = PaymentExportBuilder.build_csv_string(valid, False, cache)
        csv_file = export_file(
            filename=name,
            filetype=ExportedFile.FileType.CSV,
            content=csv.encode("utf-8"),
            cache=cache,
            send_email=False,
        )
        xml_file = export_file(
            filename=name,
            filetype=ExportedFile.FileType.XML,
            content=xml,
            cache=cache,
            send_email=False,
        )
        export = PaymentTransaction.objects.create(
            csv_file=csv_file,
            xml_file=xml_file,
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
            month=reference_date.replace(day=1),
        )
        Payment.objects.filter(pk__in=[p.pk for p in valid]).update(
            transaction=export,
            status=Payment.PaymentStatus.PAID,
            due_date=collection_date,
        )
        if send_mail:
            for file, key in [
                (csv_file, ParameterKeys.PAYMENT_SEND_CSV_FILE_PER_MAIL),
                (xml_file, ParameterKeys.PAYMENT_SEND_XML_FILE_PER_MAIL),
            ]:
                if get_parameter_value(key, cache):
                    transaction.on_commit(
                        lambda file=file: send_exported_file(file, cache, errors),
                        robust=True,
                    )
        return errors
