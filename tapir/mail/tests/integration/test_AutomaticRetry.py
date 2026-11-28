from tapir.wirgarten.parameters import ParameterDefinitions
import datetime
import smtplib
from unittest.mock import patch

from django.core import mail

from tapir.mail.models import EmailDispatch, ReleaseStatus
from tapir.mail.services.email_dispatch import RetryEmailDispatch, SendEmailBatch
from tapir.mail.tests.factories import (
    EmailConfigurationDispatchFactory,
    EmailConfigurationVersionFactory,
)
from tapir.mail.tests.integration.utils import TestUtils
from tapir.mail.tests.test_utils import mock_timezone_now
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class AutomaticRetryTest(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    NOW = datetime.datetime(2023, 9, 10, 12, 30, tzinfo=datetime.timezone.utc)

    def setUp(self):
        super().setUp()
        mock_timezone_now(self, self.NOW)
        email_config_version = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED
        )
        self.config_dispatch = EmailConfigurationDispatchFactory.create(
            email_configuration_version=email_config_version,
        )

    def send_batch_with_connection_error(self):
        with patch(
            "tapir.mail.services.email_dispatch.get_connection",
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            SendEmailBatch.send_email_dispatches()

    def get_tail(self):
        return EmailDispatch.objects.get(next_retry=None)

    def test_sendEmailDispatches_connectionError_schedulesAutomaticRetry(self):
        original = TestUtils.create_email_dispatches(
            1, config_dispatch=self.config_dispatch
        )[0]

        self.send_batch_with_connection_error()

        original.refresh_from_db()
        self.assertEqual("Connection refused", original.error_message)
        retry = original.next_retry
        self.assertIsNotNone(retry)
        self.assertTrue(retry.is_automatic_retry)
        self.assertEqual(self.NOW + datetime.timedelta(minutes=5), retry.not_before)

    def test_sendEmailDispatches_automaticRetryNotDueYet_notSent(self):
        TestUtils.create_email_dispatches(1, config_dispatch=self.config_dispatch)
        self.send_batch_with_connection_error()

        self.mock_now.return_value = self.NOW + datetime.timedelta(minutes=4)
        SendEmailBatch.send_email_dispatches()
        self.assertEqual(0, len(mail.outbox))

        self.mock_now.return_value = self.NOW + datetime.timedelta(minutes=5)
        SendEmailBatch.send_email_dispatches()
        self.assertEqual(1, len(mail.outbox))
        self.assertIsNotNone(self.get_tail().sent_time)

    def test_sendEmailDispatches_failedDispatch_notPickedUpAgain(self):
        TestUtils.create_email_dispatches(1, config_dispatch=self.config_dispatch)
        with patch(
            "tapir.mail.services.email_dispatch.build_email",
            side_effect=Exception("Template error"),
        ):
            SendEmailBatch.send_email_dispatches()

        SendEmailBatch.send_email_dispatches()

        self.assertEqual(0, len(mail.outbox))
        self.assertEqual(1, EmailDispatch.objects.count())

    def test_sendEmailDispatches_permanentSmtpError_noAutomaticRetry(self):
        TestUtils.create_email_dispatches(1, config_dispatch=self.config_dispatch)
        with patch(
            "django.core.mail.backends.locmem.EmailBackend.send_messages",
            side_effect=smtplib.SMTPResponseException(550, b"Mailbox unavailable"),
        ):
            SendEmailBatch.send_email_dispatches()

        self.assertEqual(1, EmailDispatch.objects.count())
        self.assertIsNotNone(EmailDispatch.objects.get().error_message)

    def test_sendEmailDispatches_temporarySmtpError_schedulesAutomaticRetry(self):
        TestUtils.create_email_dispatches(1, config_dispatch=self.config_dispatch)
        with patch(
            "django.core.mail.backends.locmem.EmailBackend.send_messages",
            side_effect=smtplib.SMTPResponseException(451, b"Try again later"),
        ):
            SendEmailBatch.send_email_dispatches()

        self.assertEqual(2, EmailDispatch.objects.count())
        self.assertTrue(self.get_tail().is_automatic_retry)

    def test_sendEmailDispatches_repeatedFailures_retriesThreeTimesWithIncreasingDelays(
        self,
    ):
        TestUtils.create_email_dispatches(1, config_dispatch=self.config_dispatch)
        now = self.NOW
        expected_delays = [
            datetime.timedelta(minutes=5),
            datetime.timedelta(minutes=30),
            datetime.timedelta(hours=2),
        ]

        for delay in expected_delays:
            self.send_batch_with_connection_error()
            tail = self.get_tail()
            self.assertEqual(now + delay, tail.not_before)
            now = tail.not_before
            self.mock_now.return_value = now

        self.send_batch_with_connection_error()

        self.assertEqual(4, EmailDispatch.objects.count())
        self.assertIsNotNone(self.get_tail().error_message)

    def test_retry_afterMaximumAutomaticRetries_manualRetryPossible(self):
        TestUtils.create_email_dispatches(1, config_dispatch=self.config_dispatch)
        for _ in RetryEmailDispatch.AUTOMATIC_RETRY_DELAYS:
            self.send_batch_with_connection_error()
            self.mock_now.return_value = self.get_tail().not_before
        self.send_batch_with_connection_error()

        manual_retry = RetryEmailDispatch.retry(self.get_tail())
        self.assertFalse(manual_retry.is_automatic_retry)
        self.assertIsNone(manual_retry.not_before)

        SendEmailBatch.send_email_dispatches()
        self.assertEqual(1, len(mail.outbox))

    def test_sendEmailDispatches_manualRetryFailsTemporarily_automaticRetriesRestart(
        self,
    ):
        TestUtils.create_email_dispatches(1, config_dispatch=self.config_dispatch)
        for _ in RetryEmailDispatch.AUTOMATIC_RETRY_DELAYS:
            self.send_batch_with_connection_error()
            self.mock_now.return_value = self.get_tail().not_before
        self.send_batch_with_connection_error()
        RetryEmailDispatch.retry(self.get_tail())

        self.send_batch_with_connection_error()

        tail = self.get_tail()
        self.assertTrue(tail.is_automatic_retry)
        self.assertEqual(
            self.mock_now.return_value + datetime.timedelta(minutes=5),
            tail.not_before,
        )
