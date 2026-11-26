from tapir.wirgarten.parameters import ParameterDefinitions
import time
from unittest.mock import patch

from django.core import mail

from tapir.mail.models import EmailDispatch, ReleaseStatus
from tapir.mail.service.email_dispatch import SendEmailBatch
from tapir.mail.service.tracking import get_tracking_url
from tapir.mail.tests.factories import (
    EmailConfigurationDispatchFactory,
    EmailConfigurationVersionFactory,
)
from tapir.mail.tests.integration.utils import TestUtils
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TrackingPixelTest(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self.email_config_version = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED,
            subject="Tracking",
        )
        self.config_dispatch = EmailConfigurationDispatchFactory.create(
            email_configuration_version=self.email_config_version,
        )

    def test_sendEmailDispatches_trackingPixelClicked_updatesEmailDispatchCorrectly(
        self,
    ):
        email_dispatch = TestUtils.create_email_dispatches(
            1, config_dispatch=self.config_dispatch, recipient_prefix="tracked"
        )[0]
        tracking_url = get_tracking_url(email_dispatch)

        TestUtils.create_email_dispatches(
            9, config_dispatch=self.config_dispatch, recipient_prefix="not-tracked"
        )

        SendEmailBatch.send_email_dispatches()

        # email not opened yet
        self.assertIsNone(email_dispatch.opened_time)

        # email contains tracking pixel
        self.assertIn(
            f'<img src="{tracking_url}" style="display:none"/></body>',
            mail.outbox[0].body,
        )

        # simulate tracking pixel click
        response = self.client.get(tracking_url)
        self.assertEqual(response.status_code, 200)

        # email opened time is updated
        email_dispatch.refresh_from_db()
        self.assertIsNotNone(email_dispatch.opened_time)

        original_opened_time = email_dispatch.opened_time

        # simulate tracking pixel click again
        time.sleep(1)
        response = self.client.get(tracking_url)
        self.assertEqual(response.status_code, 200)

        # email opened time is not updated
        email_dispatch.refresh_from_db()
        self.assertEqual(email_dispatch.opened_time, original_opened_time)

        # other dispatches are not affected
        self.assertEqual(
            EmailDispatch.objects.exclude(id=email_dispatch.id)
            .filter(opened_time__isnull=True)
            .count(),
            9,
        )

    def test_trackingPixelWithInternalError_stillReturns200(self):
        email_dispatch = TestUtils.create_email_dispatches(
            1, config_dispatch=self.config_dispatch
        )[0]
        tracking_url = get_tracking_url(email_dispatch)

        with patch(
            "tapir.mail.models.EmailDispatch.objects.get",
            side_effect=Exception("Mocked exception"),
        ):
            response = self.client.get(tracking_url)
            self.assertEqual(response.status_code, 200)
