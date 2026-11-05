from django.db import transaction
from django.db.models import F
from django.utils.html import format_html_join

from tapir.associations.models import AssociationDeposit
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.pain_008_xml_file_creator import Pain008XmlFileCreator
from tapir.payments.services.pain_008_xml_string_generator import (
    Pain008XmlStringGenerator,
    Pain008XmlSinglePaymentException,
    Pain008XmlGlobalException,
)
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

        collection_date = CoopSharePurchaseHandler.get_payment_due_date(
            max(reference_date, get_today(cache)), cache
        )
        pending = Payment.objects.filter(
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
            due_date__lte=collection_date,
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
        name = f"Vereinseinlagen-Einzahlungen {reference_date:%Y-%m}"
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
                cls.notify_errors(errors, name, send_mail, cache)
                return errors
            xml = Pain008XmlStringGenerator.build_xml_string(
                valid, cache, collection_date
            )
        except Pain008XmlGlobalException as error:
            errors.append(error.message)
            cls.notify_errors(errors, name, send_mail, cache)
            return errors

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
        AssociationDeposit.objects.filter(
            pk__in={p.association_deposit_id for p in valid}
        ).update(revision=F("revision") + 1)
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

    @staticmethod
    def notify_errors(errors, name, send_mail, cache: dict):
        if not send_mail:
            return
        reason = format_html_join("", "<p>{}</p>", ((error,) for error in errors))
        transaction.on_commit(
            lambda: Pain008XmlFileCreator.send_error_mail_or_raise_exception(
                reason=reason, file_name=name, cache=cache, send_mail=True
            ),
            robust=True,
        )
