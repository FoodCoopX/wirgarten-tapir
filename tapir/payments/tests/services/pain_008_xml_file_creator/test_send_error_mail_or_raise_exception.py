from unittest.mock import MagicMock

from django.core import mail
from django.test import override_settings

from tapir.payments.services.pain_008_xml_file_creator import Pain008XmlFileCreator
from tapir.payments.services.pain_008_xml_string_generator import (
    Pain008XmlGenericException,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestSendErrorMailOrRaiseException(TapirUnitTest):
    def test_sendErrorMailOrRaiseException_sendMailIsFalse_raiseGenericException(self):
        with self.assertRaises(Pain008XmlGenericException) as error:
            Pain008XmlFileCreator.send_error_mail_or_raise_exception(
                reason="test_reason",
                file_name=MagicMock(),
                cache=MagicMock(),
                send_mail=False,
            )

        self.assertEqual("test_reason", error.exception.message)

    @override_settings(
        EMAIL_HOST_SENDER="from@example.com",
        EMAIL_AUTO_BCC="bcc@example.com",
    )
    def test_sendErrorMailOrRaiseException_sendMailIsTrue_sendsMailWithErrorDetails(
        self,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.SITE_ADMIN_EMAIL, value="admin@example.com"
        )

        Pain008XmlFileCreator.send_error_mail_or_raise_exception(
            reason="test_reason",
            file_name="test_name",
            cache=cache,
            send_mail=True,
        )

        self.assertEqual(1, len(mail.outbox))
        sent_mail = mail.outbox[0]
        self.assertEqual(
            "Fehler bei der Erzeugung der test_name-Datei", sent_mail.subject
        )
        self.assertEqual(["admin@example.com"], sent_mail.to)
        self.assertEqual("from@example.com", sent_mail.from_email)
        self.assertEqual(["bcc@example.com"], sent_mail.bcc)
        self.assertEqual("html", sent_mail.content_subtype)
        self.assertEqual(
            "<p>Hallo Admin,</p><p>Die Datei test_name konnte nicht erzeugt werden. Grund dafür ist: test_reason.</p>",
            sent_mail.body,
        )
