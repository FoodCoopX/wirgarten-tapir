import datetime

from django.urls import reverse

from tapir.mail.models import ExternalRecipient, ExternalRecipientConfirmation
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class ConfirmRegistrationToMailCategoryViewTest(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_unconfirmedRegistration_storesTheCurrentTimeAsConfirmationTime(self):
        now = mock_timezone(
            test=self,
            now=datetime.datetime(
                year=2026, month=3, day=4, hour=10, tzinfo=datetime.UTC
            ),
        )
        confirmation = ExternalRecipientConfirmation.objects.create(
            external_recipient=ExternalRecipient.objects.create(
                email="external@example.com", first_name="External"
            ),
            mail_category=MailCategoryFactory.create(
                available_for_external_recipients=True
            ),
        )

        response = self.client.get(
            reverse(
                "user_confirms_registration", args=[confirmation.confirmation_secret]
            )
        )

        self.assertStatusCode(response, 200)
        confirmation.refresh_from_db()
        self.assertEqual(now, confirmation.confirmed_at)
