from tapir.wirgarten.parameters import ParameterDefinitions
import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.core import mail

from tapir.mail.config import ExternalConfig
from tapir.mail.models import EmailDispatch, ReleaseStatus
from tapir.mail.services.email import _get_dispatch_id_from_email_return_path
from tapir.mail.services.email_dispatch import RetryEmailDispatch, SendEmailBatch
from tapir.mail.services.mjml import mjml2html
from tapir.mail.tests.factories import (
    EmailConfigurationDispatchFactory,
    EmailConfigurationVersionFactory,
    EmailDispatchFactory,
)
from tapir.mail.tests.integration.utils import TestUtils
from tapir.mail.tests.test_utils import build_time_trigger_dict
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.mail.triggers.transactional_trigger import TransactionalTrigger


class SendEmailBatchTest(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    NOW = datetime.datetime(2023, 9, 10, 12, 30, tzinfo=datetime.timezone.utc)
    SUBJECT = "Test Subject"

    def setUp(self):
        self.email_config_version = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED,
            subject=self.SUBJECT,
        )
        self.config_dispatch = EmailConfigurationDispatchFactory.create(
            email_configuration_version=self.email_config_version,
        )

    def test_sendEmailDispatches_normalCase_sendsEmails(self):
        dispatches = TestUtils.create_email_dispatches(
            10, config_dispatch=self.config_dispatch
        )
        SendEmailBatch.send_email_dispatches()
        self.assertEqual(
            EmailDispatch.objects.filter(sent_time__isnull=True).count(), 0
        )
        self.assertEqual(len(mail.outbox), 10)
        for i, email in enumerate(mail.outbox):
            self.assertEqual(email.to, [f"test{i}@example.com"])
            self.assertEqual(email.subject, self.SUBJECT)
            self.assertTrue("This is a dummy email!" in str(email.body))
            self.assertEqual(
                dispatches[i].id,
                _get_dispatch_id_from_email_return_path(email.from_email),
            )

    def test_sendEmailDispatches_severalDispatchesOfSameVersion_rendersMjmlOnce(self):
        TestUtils.create_email_dispatches(3, config_dispatch=self.config_dispatch)

        with patch(
            "tapir.mail.services.email_dispatch.mjml2html",
            autospec=True,
            side_effect=mjml2html,
        ) as mock_mjml2html:
            SendEmailBatch.send_email_dispatches()

        mock_mjml2html.assert_called_once_with(self.email_config_version.content)
        self.assertEqual(3, len(mail.outbox))

    def test_sendEmailDispatches_contentHasTokens_tokensReplacedPerRecipient(self):
        self.email_config_version.content = self.email_config_version.content.replace(
            "This is a dummy email!", "Hello {{ greeting_name }}!"
        )
        self.email_config_version.save()
        dispatches = TestUtils.create_email_dispatches(
            2, config_dispatch=self.config_dispatch
        )
        for index, dispatch in enumerate(dispatches):
            dispatch.additional_tokens = {"greeting_name": f"name{index}"}
            dispatch.save()

        SendEmailBatch.send_email_dispatches()

        bodies_by_recipient = {email.to[0]: email.body for email in mail.outbox}
        self.assertIn("Hello name0!", bodies_by_recipient["test0@example.com"])
        self.assertIn("Hello name1!", bodies_by_recipient["test1@example.com"])
        self.assertNotIn("{{", bodies_by_recipient["test0@example.com"])

    def test_sendEmailDispatches_noEmailDispatches_noEmailsSent(self):
        SendEmailBatch.send_email_dispatches()
        self.assertEqual(len(mail.outbox), 0)

        TestUtils.create_email_dispatches(1, config_dispatch=self.config_dispatch)

    def test_sendEmailDispatches_errorSendingEmail_logsError(self):
        TestUtils.create_email_dispatches(1, config_dispatch=self.config_dispatch)
        with patch(
            "tapir.mail.services.email_dispatch.build_email",
            side_effect=Exception("Test exception"),
        ):
            with patch(
                "tapir.mail.services.email_dispatch.LOG.exception"
            ) as mock_log_exception:
                SendEmailBatch.send_email_dispatches()

                mock_log_exception.assert_called_once_with(
                    "Error while preparing email to test0@example.com: Test exception"
                )

                self.assertEqual(len(mail.outbox), 0)
                self.assertTrue(
                    EmailDispatch.objects.filter(
                        error_message="Test exception"
                    ).exists()
                )

    def test_sendEmailDispatches_alreadySent_noEmailsSent(self):
        TestUtils.create_email_dispatches(
            10, config_dispatch=self.config_dispatch, sent_time=self.NOW
        )
        SendEmailBatch.send_email_dispatches()
        self.assertEqual(len(mail.outbox), 0)

    def test_sendEmailDispatches_batchSizeLimit_onlyLimitSent(self):
        TestUtils.create_email_dispatches(10, config_dispatch=self.config_dispatch)
        SendEmailBatch.send_email_dispatches(batch_size=4)
        self.assertEqual(len(mail.outbox), 4)
        self.assertEqual(
            EmailDispatch.objects.filter(sent_time__isnull=True).count(), 6
        )

    def test_sendEmailDispatches_severalConfigurationsCouldBeSent_oldestGetsSent(self):
        newer_config_dispatch = EmailConfigurationDispatchFactory.create(
            email_configuration_version=self.email_config_version,
        )
        older_config_dispatch = EmailConfigurationDispatchFactory.create(
            email_configuration_version=self.email_config_version,
        )

        newer_dispatches = TestUtils.create_email_dispatches(
            10,
            config_dispatch=newer_config_dispatch,
            created_at=self.NOW,
            recipient_prefix="new",
        )
        TestUtils.create_email_dispatches(
            10,
            config_dispatch=older_config_dispatch,
            created_at=self.NOW - relativedelta(days=2),
            recipient_prefix="old",
        )

        SendEmailBatch.send_email_dispatches(batch_size=10)

        self.assertEqual(len(mail.outbox), 10)

        actual_recipients = {email.to[0] for email in mail.outbox}
        expected_recipients = {f"old{index}@example.com" for index in range(10)}
        self.assertEqual(expected_recipients, actual_recipients)

        self.assertEqual(
            set(EmailDispatch.objects.filter(sent_time__isnull=True)),
            set(newer_dispatches),
        )

    def test_retrySingleEmailDispatch_normalCase_createsRetryDispatch(self):
        dispatch = TestUtils.create_email_dispatches(
            1,
            config_dispatch=self.config_dispatch,
            error_message="Test error",
            sent_time=self.NOW,
        )[0]
        dispatch.recipient_tokens = {"test_recipient_token": "Bart"}
        dispatch.additional_tokens = {"test_additional_token": "Lisa"}
        dispatch.save()

        original_dispatch_count = EmailDispatch.objects.count()

        RetryEmailDispatch.retry(dispatch)

        # Check total dispatch count
        self.assertEqual(EmailDispatch.objects.count(), original_dispatch_count + 1)

        # Check the new dispatch
        dispatch.refresh_from_db()
        retry_dispatch: EmailDispatch = dispatch.next_retry
        self.assertEqual(retry_dispatch.recipient, dispatch.recipient)
        self.assertIsNone(retry_dispatch.sent_time)
        self.assertEqual(dispatch.recipient_tokens, retry_dispatch.recipient_tokens)
        self.assertEqual(dispatch.additional_tokens, retry_dispatch.additional_tokens)

        # Original dispatch should have a reference to the retry
        self.assertIsNotNone(dispatch.next_retry)

        # Simulate sending emails
        SendEmailBatch.send_email_dispatches()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [dispatch.recipient])

    def test_retrySingleEmailDispatch_newerVersionReleased_sendsNewerVersion(self):
        dispatch = TestUtils.create_email_dispatches(
            1,
            config_dispatch=self.config_dispatch,
            error_message="Test error",
            sent_time=self.NOW,
        )[0]
        newer_version = EmailConfigurationVersionFactory.create(
            email_configuration=self.email_config_version.email_configuration,
            status=ReleaseStatus.RELEASED,
            subject="Newer subject",
        )
        self.email_config_version.archive()

        RetryEmailDispatch.retry(dispatch)
        dispatch.refresh_from_db()

        self.assertEqual(
            newer_version, dispatch.next_retry.get_email_configuration_version()
        )
        SendEmailBatch.send_email_dispatches()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Newer subject")

    def test_retrySingleEmailDispatch_originalNotSentYet_raisesError(self):
        dispatch = TestUtils.create_email_dispatches(
            1,
            config_dispatch=self.config_dispatch,
        )[0]

        with self.assertRaises(ValueError):
            RetryEmailDispatch.retry(dispatch)

    def test_retrySingleEmailDispatch_originalSentWithoutError_createsRetryDispatch(
        self,
    ):
        dispatch = TestUtils.create_email_dispatches(
            1,
            config_dispatch=self.config_dispatch,
            sent_time=self.NOW,
        )[0]

        RetryEmailDispatch.retry(dispatch)
        dispatch.refresh_from_db()

        self.assertIsNotNone(dispatch.next_retry)
        SendEmailBatch.send_email_dispatches()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [dispatch.recipient])

    def test_retrySingleEmailDispatch_retryStillPending_raisesError(self):
        dispatch = TestUtils.create_email_dispatches(
            1,
            config_dispatch=self.config_dispatch,
            sent_time=self.NOW,
        )[0]
        RetryEmailDispatch.retry(dispatch)

        with self.assertRaises(ValueError):
            RetryEmailDispatch.retry(dispatch)

    def test_retrySingleEmailDispatch_retryOfRetry_refersBackToOriginalDispatch(self):
        original_dispatch = TestUtils.create_email_dispatches(
            1,
            config_dispatch=self.config_dispatch,
            error_message="Initial error",
            sent_time=self.NOW,
        )[0]

        # Retry the original dispatch
        RetryEmailDispatch.retry(original_dispatch)
        original_dispatch.refresh_from_db()

        # Get the created retry dispatch
        first_retry_dispatch = original_dispatch.next_retry
        first_retry_dispatch.error_message = "First retry error"
        first_retry_dispatch.sent_time = self.NOW
        first_retry_dispatch.save()

        # Retry the first retry dispatch
        RetryEmailDispatch.retry(first_retry_dispatch)
        first_retry_dispatch.refresh_from_db()

        # Get the second retry dispatch
        second_retry_dispatch = first_retry_dispatch.next_retry

        # Check the chain of retries
        self.assertIsNotNone(first_retry_dispatch)
        self.assertIsNotNone(second_retry_dispatch)
        self.assertEqual(original_dispatch.next_retry, first_retry_dispatch)
        self.assertEqual(first_retry_dispatch.next_retry, second_retry_dispatch)

        SendEmailBatch.send_email_dispatches()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [original_dispatch.recipient])

    def test_retryAllFailed_mixOfFailedAndSucceeded_onlyEligibleDispatchesAreRetried(
        self,
    ):
        error_dispatches = TestUtils.create_email_dispatches(
            2,
            config_dispatch=self.config_dispatch,
            error_message="Error",
            sent_time=self.NOW,
        )
        TestUtils.create_email_dispatches(
            1,
            config_dispatch=self.config_dispatch,
            sent_time=self.NOW,
        )

        # Retry one of the error dispatches to create a retry dispatch
        RetryEmailDispatch.retry(error_dispatches[0])

        original_retries_count = EmailDispatch.objects.filter(
            next_retry__isnull=False
        ).count()

        RetryEmailDispatch.retry_all_failed(self.config_dispatch)

        new_retries_count = EmailDispatch.objects.filter(
            next_retry__isnull=False
        ).count()

        self.assertEqual(new_retries_count, original_retries_count + 1)

    def test_retryAllFailed_noEligibleDispatches_noRetriesCreated(self):
        RetryEmailDispatch.retry_all_failed(self.config_dispatch)

        # Verify that no new retries were created
        self.assertEqual(
            EmailDispatch.objects.filter(next_retry__isnull=False).count(), 0
        )

    def test_sendEmailDispatches_mailIsMassMailAndBccProviderDefined_sendMailWithBcc(
        self,
    ):
        email_dispatch = EmailDispatchFactory.create(
            sent_time=None,
            email_configuration_dispatch__email_configuration_version__status=ReleaseStatus.RELEASED,
        )
        email_dispatch.email_configuration_dispatch.email_configuration_version.triggers = [
            build_time_trigger_dict(
                scheduled_time=self.NOW - datetime.timedelta(days=1)
            )
        ]
        email_dispatch.email_configuration_dispatch.email_configuration_version.save()

        ExternalConfig.MASS_MAIL_BCC_PROVIDER = lambda: "test_bcc@example.com"

        SendEmailBatch.send_email_dispatches(batch_size=1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(["test_bcc@example.com"], mail.outbox[0].bcc)

    def test_sendEmailDispatches_mailIsMassMailAndBccProviderNotDefined_sendMailWithoutBcc(
        self,
    ):
        email_dispatch = EmailDispatchFactory.create(
            sent_time=None,
            email_configuration_dispatch__email_configuration_version__status=ReleaseStatus.RELEASED,
        )
        email_dispatch.email_configuration_dispatch.email_configuration_version.triggers = [
            build_time_trigger_dict(
                scheduled_time=self.NOW - datetime.timedelta(days=1)
            )
        ]
        email_dispatch.email_configuration_dispatch.email_configuration_version.save()

        ExternalConfig.MASS_MAIL_BCC_PROVIDER = None

        SendEmailBatch.send_email_dispatches(batch_size=1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual([], mail.outbox[0].bcc)

    def test_sendEmailDispatches_mailIsMassMailAndBccProviderGivesEmptyValue_sendMailWithoutBcc(
        self,
    ):
        email_dispatch = EmailDispatchFactory.create(
            sent_time=None,
            email_configuration_dispatch__email_configuration_version__status=ReleaseStatus.RELEASED,
        )
        email_dispatch.email_configuration_dispatch.email_configuration_version.triggers = [
            build_time_trigger_dict(
                scheduled_time=self.NOW - datetime.timedelta(days=1)
            )
        ]
        email_dispatch.email_configuration_dispatch.email_configuration_version.save()

        ExternalConfig.MASS_MAIL_BCC_PROVIDER = lambda: ""

        SendEmailBatch.send_email_dispatches(batch_size=1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual([], mail.outbox[0].bcc)

    def test_sendEmailDispatches_mailIsTransactionalMailAndProviderIsDefined_sendMailWithBcc(
        self,
    ):
        email_dispatch = EmailDispatchFactory.create(
            sent_time=None,
            email_configuration_dispatch__email_configuration_version__status=ReleaseStatus.RELEASED,
        )
        email_dispatch.email_configuration_dispatch.email_configuration_version.triggers = [
            {"trigger_id": TransactionalTrigger.get_id()}
        ]
        email_dispatch.email_configuration_dispatch.email_configuration_version.save()

        ExternalConfig.MASS_MAIL_BCC_PROVIDER = lambda: "mass_mail_bcc@example.com"
        ExternalConfig.TRANSACTIONAL_MAIL_BCC_PROVIDER = (
            lambda: "transactional_mail_bcc@example.com"
        )

        SendEmailBatch.send_email_dispatches(batch_size=1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(["transactional_mail_bcc@example.com"], mail.outbox[0].bcc)
