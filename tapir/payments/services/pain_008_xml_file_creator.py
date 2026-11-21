import datetime
from datetime import date

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.pain_008_xml_string_generator import (
    Pain008XmlStringGenerator,
    Pain008XmlGlobalException,
    Pain008XmlSinglePaymentException,
    Pain008XmlGenericException,
)
from tapir.wirgarten.models import (
    Payment,
    ExportedFile,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.file_export import export_file


class Pain008XmlFileCreator:
    @classmethod
    def create_xml_file_and_send_mail(
        cls,
        payments: list[Payment],
        file_name: str,
        reference_date: date,
        send_mail: bool,
        cache: dict,
    ) -> tuple[ExportedFile | None, list[str]]:
        try:
            xml_bytes, errors_failed_payments = (
                cls.build_xml_string_with_valid_payments_and_errors_for_invalid_payments(
                    payments=payments,
                    collection_date=reference_date,
                    cache=cache,
                )
            )
        except Pain008XmlGlobalException as exception:
            cls.send_error_mail_or_raise_exception(
                reason=exception.message,
                file_name=file_name,
                cache=cache,
                send_mail=send_mail,
            )
            return None, []

        if xml_bytes is None:
            reason = f"<ul><li>{"</li><li>".join(errors_failed_payments)}</li></ul>"
            cls.send_error_mail_or_raise_exception(
                reason=reason, file_name=file_name, cache=cache, send_mail=send_mail
            )
            return None, []

        xml_file = export_file(
            filename=file_name,
            filetype=ExportedFile.FileType.XML,
            content=xml_bytes,
            send_email=send_mail
            and get_parameter_value(
                key=ParameterKeys.PAYMENT_SEND_XML_FILE_PER_MAIL, cache=cache
            ),
            cache=cache,
            errors=errors_failed_payments,
        )
        return xml_file, errors_failed_payments

    @classmethod
    def send_error_mail_or_raise_exception(
        cls, reason: str, file_name: str, cache: dict, send_mail: bool
    ):
        if not send_mail:
            raise Pain008XmlGenericException(message=reason)

        subject = f"Fehler bei der Erzeugung der {file_name}-Datei"

        body = f"<p>Hallo Admin,</p><p>Die Datei {file_name} konnte nicht erzeugt werden. Grund dafür ist: {reason}.</p>"

        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            to=[get_parameter_value(ParameterKeys.SITE_ADMIN_EMAIL, cache=cache)],
            from_email=settings.EMAIL_HOST_SENDER,
            bcc=(
                [settings.EMAIL_AUTO_BCC]
                if hasattr(settings, "EMAIL_AUTO_BCC") and settings.EMAIL_AUTO_BCC
                else None
            ),
        )
        email.content_subtype = "html"
        email.send()

    @classmethod
    def build_xml_string_with_valid_payments_and_errors_for_invalid_payments(
        cls, payments: list[Payment], collection_date: datetime.date, cache: dict
    ) -> tuple[bytes | None, list[str]]:
        errors = []
        valid_payments = []
        for payment in payments:
            try:
                Pain008XmlStringGenerator.validate_single_payment(
                    payment=payment, collection_date=collection_date, cache=cache
                )
                valid_payments.append(payment)
            except Pain008XmlSinglePaymentException as exception:
                errors.append(exception.message)

        xml_string = None
        if len(valid_payments) > 0:
            xml_string = Pain008XmlStringGenerator.build_xml_string(
                payments=valid_payments, collection_date=collection_date, cache=cache
            )

        return xml_string, errors
