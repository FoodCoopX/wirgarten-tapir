import datetime
import uuid

from django.urls import reverse

from tapir.mail.models import (
    ExternalRecipient,
    ExternalRecipientConfirmation,
    StaticSegmentRecipient,
)
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestConfirmRegistrationToMailCategoryViewGet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_unconfirmedRegistration_showsConfirmationButtonWithoutConfirming(
        self,
    ):
        confirmation = self._create_confirmation(confirmed_at=None)

        response = self.client.get(self._get_url(confirmation.confirmation_secret))

        self.assertStatusCode(response, 200)
        self.assertTemplateUsed(response, "tapir_mail/confirm_registration.html")
        self.assertContains(response, "Anmeldung bestätigen")
        confirmation.refresh_from_db()
        self.assertIsNone(confirmation.confirmed_at)
        self.assertFalse(StaticSegmentRecipient.objects.exists())

    def test_get_confirmedRegistration_showsSuccessPage(self):
        confirmation = self._create_confirmation(
            confirmed_at=datetime.datetime(
                year=2026, month=1, day=1, tzinfo=datetime.UTC
            )
        )

        response = self.client.get(self._get_url(confirmation.confirmation_secret))

        self.assertStatusCode(response, 200)
        self.assertTemplateUsed(
            response, "tapir_mail/confirmation_registration_complete.html"
        )
        self.assertContains(response, confirmation.mail_category.name)

    def test_get_unknownSecret_returns404(self):
        response = self.client.get(self._get_url(uuid.uuid4()))

        self.assertStatusCode(response, 404)

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
