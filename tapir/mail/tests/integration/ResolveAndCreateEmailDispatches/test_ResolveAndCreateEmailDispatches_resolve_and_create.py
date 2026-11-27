from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from django.core.cache import cache

from tapir.mail.models import (
    EmailConfigurationDispatch,
    EmailDispatch,
    ReleaseStatus,
)
from tapir.mail.services.email_dispatch import (
    ResolveAndCreateEmailDispatches,
    LOG,
)
from tapir.mail.tests.factories import (
    EmailConfigurationVersionFactory,
    StaticSegmentFactory,
    StaticSegmentRecipientFactory,
)
from tapir.mail.tests.test_utils import mock_timezone_now
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestResolveAndCreateEmailDispatchesResolveAndCreate(TapirIntegrationTest):
    NOW = datetime(2023, 9, 10, 12, 30, tzinfo=timezone.utc)
    RECIPIENT_COUNT = 10

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

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

    def test_resolveAndCreate_normalCase_createsDispatches(self):
        self._create_email_config_dispatch(scheduled_time=self.NOW)
        self.email_config_version.static_segments_additive.set([self.segment])
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), self.RECIPIENT_COUNT)

    def test_resolveAndCreate_noConfigDispatches_noDispatchesCreated(self):
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)

    def test_resolveAndCreate_noRecipients_noDispatchesCreated(self):
        config_dispatch = self._create_email_config_dispatch(scheduled_time=self.NOW)
        config_dispatch.override_recipients = []
        config_dispatch.save()
        with self.assertLogs(LOG, level="ERROR") as logs:
            ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)
        self.assertEqual(1, len(logs.records))

    def test_resolveAndCreate_alreadySent_noDispatchesCreated(self):
        self._create_email_config_dispatch(scheduled_time=self.NOW, is_sent=True)
        with self.assertNoLogs(LOG, level="ERROR"):
            ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)

    def test_resolveAndCreate_scheduledFuture_noDispatchesCreated(self):
        future_time = self.NOW + relativedelta(days=1)
        self._create_email_config_dispatch(scheduled_time=future_time)
        with self.assertNoLogs(LOG, level="ERROR"):
            ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)

    def test_resolveAndCreate_moreThan10Dispatches_only10Processed(self):
        self.email_config_version.static_segments_additive.set([self.segment])
        for _ in range(15):
            self._create_email_config_dispatch(scheduled_time=self.NOW)
        ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 10 * self.RECIPIENT_COUNT)

    def test_resolveAndCreate_notReleased_noDispatchesCreated(self):
        self.email_config_version.status = ReleaseStatus.DRAFT
        self.email_config_version.save()
        self._create_email_config_dispatch(scheduled_time=self.NOW)
        with self.assertNoLogs(LOG, level="ERROR"):
            ResolveAndCreateEmailDispatches.resolve_and_create()
        self.assertEqual(EmailDispatch.objects.count(), 0)

    def test_resolveAndCreate_failCreateDispatches_retryIncrementedOnFailure(self):
        config_dispatch = self._create_email_config_dispatch(scheduled_time=self.NOW)

        with self.assertLogs(LOG, level="ERROR"):
            ResolveAndCreateEmailDispatches.resolve_and_create()

        cache_key = f"dispatch_retry_count_{config_dispatch.id}"
        retry_count = cache.get(cache_key, 0)

        self.assertEqual(retry_count, 1)
        self.assertEqual(EmailDispatch.objects.count(), 0)

    def test_resolveAndCreate_failMultipleTimes_givesUpAfterMaxRetries(self):
        config_dispatch = self._create_email_config_dispatch(scheduled_time=self.NOW)

        with self.assertLogs(LOG, level="ERROR"):
            for _ in range(ResolveAndCreateEmailDispatches.MAX_RETRIES + 1):
                ResolveAndCreateEmailDispatches.resolve_and_create()

        config_dispatch.email_configuration_version.refresh_from_db()
        self.assertEqual(
            config_dispatch.email_configuration_version.status, ReleaseStatus.ERROR
        )
        self.assertEqual(EmailDispatch.objects.count(), 0)

    def test_resolveAndCreate_failAndThenSucceed_resetOnSuccess(self):
        config_dispatch = self._create_email_config_dispatch(scheduled_time=self.NOW)
        cache_key = f"dispatch_retry_count_{config_dispatch.id}"

        with self.assertLogs(LOG, level="ERROR"):
            ResolveAndCreateEmailDispatches.resolve_and_create()

        self.assertEqual(1, cache.get(cache_key, 0))
        self.assertEqual(EmailDispatch.objects.count(), 0)

        self.email_config_version.static_segments_additive.set([self.segment])
        ResolveAndCreateEmailDispatches.resolve_and_create()

        self.assertIsNone(cache.get(cache_key, None))
        self.assertEqual(EmailDispatch.objects.count(), self.RECIPIENT_COUNT)

    def _create_email_config_dispatch(
        self, scheduled_time: datetime, is_sent: bool = False
    ) -> EmailConfigurationDispatch:
        return EmailConfigurationDispatch.objects.create(
            email_configuration_version=self.email_config_version,
            scheduled_time=scheduled_time,
            is_sent=is_sent,
        )
