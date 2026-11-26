from tapir.wirgarten.parameters import ParameterDefinitions
from datetime import datetime, timezone
from unittest.mock import patch, Mock

from dateutil.relativedelta import relativedelta
from django.core.cache import cache

from tapir.mail.models import (
    EmailConfigurationDispatch,
    EmailDispatch,
    ReleaseStatus,
)
from tapir.mail.services.email_dispatch import ResolveAndCreateEmailDispatches
from tapir.mail.services.recipient_list_provider import RecipientListProvider
from tapir.mail.services.token import register_tokens
from tapir.mail.tests.factories import (
    EmailConfigurationVersionFactory,
    StaticSegmentFactory,
    StaticSegmentRecipientFactory,
)
from tapir.mail.tests.test_utils import mock_timezone_now
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.tests.factories import MemberFactory


class ResolveAndCreateEmailDispatchesTest(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    NOW = datetime(2023, 9, 10, 12, 30, tzinfo=timezone.utc)
    RECIPIENT_COUNT = 10

    def setUp(self):
        mock_timezone_now(self, self.NOW)
        self.email_config_version = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED
        )

        self.segment = StaticSegmentFactory.create(name="Test Segment")

        for _ in range(self.RECIPIENT_COUNT):
            StaticSegmentRecipientFactory.create(
                segment=self.segment,
            )

    def create_email_config_dispatch(self, scheduled_time, is_sent=False):
        return EmailConfigurationDispatch.objects.create(
            email_configuration_version=self.email_config_version,
            scheduled_time=scheduled_time,
            is_sent=is_sent,
        )

    def test_resolveAndCreate_normalCase_createsDispatches(self):
        self.create_email_config_dispatch(scheduled_time=self.NOW)
        self.email_config_version.static_segments_additive.set([self.segment])
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), self.RECIPIENT_COUNT)

    def test_resolveAndCreate_noConfigDispatches_noDispatchesCreated(self):
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)

    @patch("tapir.mail.services.email_dispatch.LOG.error")
    def test_resolveAndCreate_noRecipients_noDispatchesCreated(self, mock_log_error):
        config_dispatch = self.create_email_config_dispatch(scheduled_time=self.NOW)
        config_dispatch.override_recipients = []
        config_dispatch.save()
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)
        mock_log_error.assert_called_once()

    @patch("tapir.mail.services.email_dispatch.LOG.error")
    def test_resolveAndCreate_errorCreatingDispatches_logsError(self, mock_log_error):
        config_dispatch = self.create_email_config_dispatch(scheduled_time=self.NOW)
        config_dispatch.email_configuration_version.segment_data = None
        config_dispatch.email_configuration_version.save()
        ResolveAndCreateEmailDispatches.resolve_and_create()
        mock_log_error.assert_called_once()

    def test_createEmailDispatches_noSegmentData_raisesValueError(self):
        config_dispatch = self.create_email_config_dispatch(scheduled_time=self.NOW)
        config_dispatch.email_configuration_version.segment_data = None
        config_dispatch.email_configuration_version.save()
        with self.assertRaises(ValueError):
            ResolveAndCreateEmailDispatches._create_email_dispatches(config_dispatch)

    def test_createEmailDispatches_noRecipients_raisesValueError(self):
        config_dispatch = self.create_email_config_dispatch(scheduled_time=self.NOW)
        config_dispatch.override_recipients = []
        config_dispatch.save()
        with self.assertRaises(ValueError):
            ResolveAndCreateEmailDispatches._create_email_dispatches(config_dispatch)

    def test_getEmailConfigurationDispatchesThatShouldBeSent_normalCase_returnsDispatches(
        self,
    ):
        for _ in range(10):
            self.create_email_config_dispatch(scheduled_time=self.NOW)
        result = (
            ResolveAndCreateEmailDispatches._get_email_configuration_dispatches_that_should_be_sent()
        )
        self.assertEqual(len(result), 10)

    @patch("tapir.mail.services.email_dispatch.LOG.error")
    def test_resolveAndCreate_alreadySent_noDispatchesCreated(self, mock_log_error):
        self.create_email_config_dispatch(scheduled_time=self.NOW, is_sent=True)
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)
        mock_log_error.assert_not_called()

    @patch("tapir.mail.services.email_dispatch.LOG.error")
    def test_resolveAndCreate_scheduledFuture_noDispatchesCreated(self, mock_log_error):
        future_time = self.NOW + relativedelta(days=1)
        self.create_email_config_dispatch(scheduled_time=future_time)
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)
        mock_log_error.assert_not_called()

    def test_resolveAndCreate_moreThan10Dispatches_only10Processed(self):
        self.email_config_version.static_segments_additive.set([self.segment])
        for _ in range(15):
            self.create_email_config_dispatch(scheduled_time=self.NOW)
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 10 * self.RECIPIENT_COUNT)

    @patch("tapir.mail.services.email_dispatch.LOG.error")
    def test_resolveAndCreate_notReleased_noDispatchesCreated(self, mock_log_error):
        self.email_config_version.status = ReleaseStatus.DRAFT
        self.email_config_version.save()
        self.create_email_config_dispatch(scheduled_time=self.NOW)
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)
        mock_log_error.assert_not_called()

    @patch("tapir.mail.tasks.ResolveAndCreateEmailDispatches._create_email_dispatches")
    def test_resolveAndCreate_failCreateDispatches_retryIncrementedOnFailure(
        self, mock_create_dispatches
    ):
        mock_create_dispatches.side_effect = Exception("Test failure")
        config_dispatch = self.create_email_config_dispatch(scheduled_time=self.NOW)

        ResolveAndCreateEmailDispatches.resolve_and_create()

        cache_key = f"dispatch_retry_count_{config_dispatch.id}"
        retry_count = cache.get(cache_key, 0)

        self.assertEqual(retry_count, 1)
        self.assertEqual(EmailDispatch.objects.count(), 0)

    @patch.object(
        RecipientListProvider, "get_recipient_list_from_email_configuration_dispatch"
    )
    def test_resolveAndCreate_failResolveSegments_retryIncrementedOnFailure(
        self, mock_get_recipient_list_from_email_configuration_dispatch
    ):
        mock_get_recipient_list_from_email_configuration_dispatch.side_effect = (
            Exception("Test failure")
        )
        config_dispatch = self.create_email_config_dispatch(scheduled_time=self.NOW)

        ResolveAndCreateEmailDispatches.resolve_and_create()

        cache_key = f"dispatch_retry_count_{config_dispatch.id}"
        retry_count = cache.get(cache_key, 0)

        self.assertEqual(retry_count, 1)
        self.assertEqual(EmailDispatch.objects.count(), 0)

    @patch("tapir.mail.tasks.ResolveAndCreateEmailDispatches._create_email_dispatches")
    def test_resolveAndCreate_failMultipleTimes_givesUpAfterMaxRetries(
        self, mock_create_dispatches
    ):
        config_dispatch = self.create_email_config_dispatch(scheduled_time=self.NOW)

        mock_create_dispatches.side_effect = Exception("Test failure")

        for _ in range(ResolveAndCreateEmailDispatches.MAX_RETRIES + 1):
            ResolveAndCreateEmailDispatches.resolve_and_create()

        config_dispatch.email_configuration_version.refresh_from_db()
        self.assertEqual(
            config_dispatch.email_configuration_version.status, ReleaseStatus.ERROR
        )
        self.assertEqual(EmailDispatch.objects.count(), 0)

    def test_resolveAndCreate_failAndThenSucceed_resetOnSuccess(self):
        config_dispatch = self.create_email_config_dispatch(scheduled_time=self.NOW)
        cache_key = f"dispatch_retry_count_{config_dispatch.id}"
        self.email_config_version.static_segments_additive.set([self.segment])

        # First, simulate a failure
        with patch(
            "tapir.mail.tasks.ResolveAndCreateEmailDispatches._create_email_dispatches"
        ) as mock_create_dispatches:
            mock_create_dispatches.side_effect = Exception("Test failure")
            ResolveAndCreateEmailDispatches.resolve_and_create()

            retry_count = cache.get(cache_key, 0)

            self.assertEqual(retry_count, 1)
            self.assertEqual(EmailDispatch.objects.count(), 0)

        # Now, simulate a success
        ResolveAndCreateEmailDispatches.resolve_and_create()

        retry_count = cache.get(cache_key, None)
        self.assertIsNone(retry_count)
        self.assertEqual(EmailDispatch.objects.count(), self.RECIPIENT_COUNT)

    @patch.object(
        RecipientListProvider,
        "get_recipient_list_from_email_configuration_dispatch",
        autospec=True,
    )
    def test_createEmailDispatches_someRecipientsHaveExtraAddresses_createsADispatchForEachRecipientAndExtras(
        self, mock_get_recipient_list_from_email_configuration_dispatch: Mock
    ):
        config_dispatch = self.create_email_config_dispatch(scheduled_time=self.NOW)
        self.email_config_version.content = "FirstName:{{Empfänger.Vorname}} LastName:{{Empfänger.Nachname}} Email:{{Empfänger.Email}} IBAN:{{Empfänger.IBAN}}"
        self.email_config_version.save()
        register_tokens(
            user_tokens={
                "Vorname": "first_name",
                "Nachname": "last_name",
                "IBAN": "iban",
                "Email": "email",
            },
            dynamic_tokens={},
            general_tokens={},
        )
        static_recipient = StaticSegmentRecipientFactory.create(
            email="static@example.com", first_name="FN-static", last_name="LN-static"
        )
        dynamic_recipient_without_extra = MemberFactory.create(
            email="noextra@example.com",
            first_name="FN-noextra",
            last_name="LN-noextra",
            iban="IBAN-noextra",
        )
        dynamic_recipient_with_extras = MemberFactory.create(
            email="withextra@example.com",
            first_name="FN-withextra",
            last_name="LN-withextra",
            iban="IBAN-withextra",
        )
        extra_recipient_1 = Mock(
            email="extra1@example.com",
            first_name="FN-extra1",
            last_name="LN-extra1",
            iban="IBAN-extra1",
        )
        extra_recipient_2 = Mock(
            email="extra2@example.com",
            first_name="FN-extra2",
            last_name="LN-extra2",
            iban="IBAN-extra2",
        )
        setattr(
            dynamic_recipient_with_extras,
            "get_extra_recipients",
            lambda _: [extra_recipient_1, extra_recipient_2],
        )

        mock_get_recipient_list_from_email_configuration_dispatch.return_value = [
            static_recipient,
            dynamic_recipient_without_extra,
            dynamic_recipient_with_extras,
        ]

        ResolveAndCreateEmailDispatches._create_email_dispatches(config_dispatch)

        self.assertEqual(5, EmailDispatch.objects.count())
        actual_addresses = set(
            EmailDispatch.objects.values_list("recipient", flat=True)
        )
        expected_addresses = {
            "static@example.com",
            "noextra@example.com",
            "withextra@example.com",
            "extra1@example.com",
            "extra2@example.com",
        }
        self.assertEqual(expected_addresses, actual_addresses)

        email_dispatches = {
            key: EmailDispatch.objects.get(recipient=f"{key}@example.com")
            for key in ["static", "noextra", "withextra", "extra1", "extra2"]
        }

        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-static",
                "last_name": "LN-static",
                "email": "static@example.com",
                "iban": "",
            },
            email_dispatches["static"].recipient_tokens,
        )
        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-noextra",
                "last_name": "LN-noextra",
                "email": "noextra@example.com",
                "iban": "IBAN-noextra",
            },
            email_dispatches["noextra"].recipient_tokens,
        )
        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-withextra",
                "last_name": "LN-withextra",
                "email": "withextra@example.com",
                "iban": "IBAN-withextra",
            },
            email_dispatches["withextra"].recipient_tokens,
        )
        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-extra1",
                "last_name": "LN-extra1",
                "email": "withextra@example.com",
                "iban": "IBAN-withextra",
            },
            email_dispatches["extra1"].recipient_tokens,
        )  # The first and last names should be overridden with the values from the extra recipient, but all other tokens should stay the same
        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-extra2",
                "last_name": "LN-extra2",
                "email": "withextra@example.com",
                "iban": "IBAN-withextra",
            },
            email_dispatches["extra2"].recipient_tokens,
        )

    def _assert_recipient_tokens_are_correct(
        self, expected_tokens: dict, actual_tokens: dict
    ):
        for token in ["first_name", "last_name", "email", "iban"]:
            self.assertEqual(expected_tokens[token], actual_tokens[token])
