import datetime
from django.core import mail
from unittest.mock import patch, Mock
from tapir.mail.models import EmailConfigurationDispatch, EmailDispatch, ReleaseStatus
from django.core.cache import cache
from tapir.mail.services.email_dispatch import (
    ResolveAndCreateEmailDispatches,
)
from tapir.mail.tests.test_utils import mock_timezone_now
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestResolveAndCreateEmailDispatches(TapirUnitTest):
    NOW = datetime.datetime(
        year=2023, month=9, day=10, hour=12, minute=30, tzinfo=datetime.UTC
    )

    @patch.object(EmailConfigurationDispatch.objects, "filter")
    def test_getEmailConfigurationDispatchesThatShouldBeSent_returnsCorrectFilter(
        self, mock_filter: Mock
    ):
        mock_timezone_now(self, self.NOW)
        result = (
            ResolveAndCreateEmailDispatches._get_email_configuration_dispatches_that_should_be_sent()
        )
        mock_filter.assert_called_once_with(
            is_sent=False,
            scheduled_time__lte=self.NOW,
            email_configuration_version__status=ReleaseStatus.RELEASED,
        )
        self.assertEqual(mock_filter.return_value, result)

    @patch.object(cache, "lock")
    @patch.object(ResolveAndCreateEmailDispatches, "_create_email_dispatches")
    @patch.object(EmailConfigurationDispatch.objects, "filter")
    def test_resolveAndCreate_severalConfigToSend_createsEmailDispatches(
        self, mock_filter, mock_create_dispatches, mock_lock
    ):
        mock_lock_instance = Mock()
        mock_lock.return_value = mock_lock_instance
        mock_lock_instance.acquire.return_value = True
        mock_config = Mock()
        mock_filter.return_value.order_by.return_value = [mock_config] * 10

        ResolveAndCreateEmailDispatches.resolve_and_create()

        self.assertEqual(10, mock_create_dispatches.call_count)
        shared_cache = mock_create_dispatches.call_args_list[0].kwargs["cache"]
        for call in mock_create_dispatches.call_args_list:
            self.assertEqual(
                {"config_dispatch": mock_config, "cache": shared_cache}, call.kwargs
            )
            self.assertIs(shared_cache, call.kwargs["cache"])
        mock_lock_instance.release.assert_called_once()
