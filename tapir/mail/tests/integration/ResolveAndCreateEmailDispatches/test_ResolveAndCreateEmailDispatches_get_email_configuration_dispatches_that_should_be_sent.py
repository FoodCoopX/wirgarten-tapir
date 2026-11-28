from datetime import datetime, timezone

from tapir.mail.models import EmailConfigurationDispatch, ReleaseStatus
from tapir.mail.services.email_dispatch import ResolveAndCreateEmailDispatches
from tapir.mail.tests.factories import EmailConfigurationVersionFactory
from tapir.mail.tests.test_utils import mock_timezone_now
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestResolveAndCreateEmailDispatchesGetEmailConfigurationDispatchesThatShouldBeSent(
    TapirIntegrationTest
):
    NOW = datetime(2023, 9, 10, 12, 30, tzinfo=timezone.utc)

    def setUp(self):
        mock_timezone_now(self, self.NOW)
        self.email_config_version = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED
        )

    def test_getEmailConfigurationDispatchesThatShouldBeSent_normalCase_returnsDispatches(
        self,
    ):
        for _ in range(10):
            self._create_email_config_dispatch(scheduled_time=self.NOW)
        result = (
            ResolveAndCreateEmailDispatches._get_email_configuration_dispatches_that_should_be_sent()
        )
        self.assertEqual(len(result), 10)

    def _create_email_config_dispatch(
        self, scheduled_time: datetime, is_sent: bool = False
    ) -> EmailConfigurationDispatch:
        return EmailConfigurationDispatch.objects.create(
            email_configuration_version=self.email_config_version,
            scheduled_time=scheduled_time,
            is_sent=is_sent,
        )
