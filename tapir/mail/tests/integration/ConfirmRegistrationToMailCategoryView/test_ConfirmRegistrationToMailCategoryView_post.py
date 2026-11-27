import datetime
import uuid
from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.urls import reverse

from tapir.mail.config import TransactionalTriggerKeys
from tapir.mail.models import (
    ExternalRecipient,
    ExternalRecipientConfirmation,
    StaticSegmentRecipient,
)
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.mail.triggers.transactional_trigger import TransactionalTrigger
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


@patch.object(TransactionalTrigger, "fire_action", autospec=True)
class TestConfirmRegistrationToMailCategoryViewPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @override_settings(SITE_URL="http://localhost")
    def test_post_unconfirmedRegistration_confirmsRegistersAndRedirects(
        self, mock_fire_action: MagicMock
    ):
        now = mock_timezone(
            test=self,
            now=datetime.datetime(
                year=2026, month=3, day=4, hour=10, tzinfo=datetime.UTC
            ),
        )
        confirmation = self._create_confirmation(confirmed_at=None)
        url = self._get_url(confirmation.confirmation_secret)

        response = self.client.post(url)

        self.assertRedirects(response, url, fetch_redirect_response=False)
        confirmation.refresh_from_db()
        self.assertEqual(now, confirmation.confirmed_at)
        self.assertEqual(
            ["external@example.com"],
            list(
                StaticSegmentRecipient.objects.filter(
                    segment_id=confirmation.mail_category.static_segment_id
                ).values_list("email", flat=True)
            ),
        )
        mock_fire_action.assert_called_once()
        self.assertEqual(
            TransactionalTriggerKeys.MAIL_CATEGORY_REGISTRATION_CONFIRMED,
            mock_fire_action.call_args.args[0].key,
        )
        self.assertEqual(
            "http://localhost" + reverse("core:subscription_management_link_request"),
            mock_fire_action.call_args.args[0].token_data["management_link"],
        )

    def test_post_alreadyConfirmedRegistration_changesNothingAndRedirects(
        self, mock_fire_action: MagicMock
    ):
        confirmed_at = datetime.datetime(year=2026, month=1, day=1, tzinfo=datetime.UTC)
        confirmation = self._create_confirmation(confirmed_at=confirmed_at)
        url = self._get_url(confirmation.confirmation_secret)

        response = self.client.post(url)

        self.assertRedirects(response, url, fetch_redirect_response=False)
        confirmation.refresh_from_db()
        self.assertEqual(confirmed_at, confirmation.confirmed_at)
        self.assertFalse(StaticSegmentRecipient.objects.exists())
        mock_fire_action.assert_not_called()

    def test_post_unknownSecret_returns404(self, mock_fire_action: MagicMock):
        response = self.client.post(self._get_url(uuid.uuid4()))

        self.assertStatusCode(response, 404)
        mock_fire_action.assert_not_called()

    @staticmethod
    def _create_confirmation(
        confirmed_at: datetime.datetime | None,
    ) -> ExternalRecipientConfirmation:
        return ExternalRecipientConfirmation.objects.create(
            external_recipient=ExternalRecipient.objects.create(
                email="external@example.com", first_name="External"
            ),
            mail_category=MailCategoryFactory.create(
                available_for_external_recipients=True
            ),
            confirmed_at=confirmed_at,
        )

    @staticmethod
    def _get_url(secret: uuid.UUID) -> str:
        return reverse("user_confirms_registration", args=[secret])
