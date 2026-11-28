from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status

from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.mail.models import (
    ExternalRecipient,
    ExternalRecipientConfirmation,
    StaticSegmentRecipient,
)
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(
    SubscriptionManagementTokenSigner,
    "get_address",
    autospec=True,
    return_value="external@example.com",
)
class TestSubscriptionManagementExternalApiViewPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_tokenIsInvalid_returns403(self, mock_get_address: MagicMock):
        mock_get_address.return_value = None

        response = self._post(first_name="New", categories_registered_to={})

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_addressIsNotAnExternalRecipient_returns404(self, _: MagicMock):
        response = self._post(first_name="New", categories_registered_to={})

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_post_default_updatesTheFirstNameAndTheRegistrations(self, _: MagicMock):
        external_recipient = ExternalRecipient.objects.create(
            email="external@example.com", first_name="Old"
        )
        to_register = MailCategoryFactory.create()
        to_remove = MailCategoryFactory.create()
        untouched = MailCategoryFactory.create()
        for category in [to_remove, untouched]:
            StaticSegmentRecipient.objects.create(
                segment=category.static_segment,
                email="external@example.com",
                first_name="Old",
            )
        ExternalRecipientConfirmation.objects.create(
            external_recipient=external_recipient, mail_category=to_remove
        )

        response = self._post(
            first_name=" New ",
            categories_registered_to={to_register.id: True, to_remove.id: False},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        external_recipient.refresh_from_db()
        self.assertEqual("New", external_recipient.first_name)
        self.assertEqual(
            {
                (to_register.static_segment_id, "New"),
                (untouched.static_segment_id, "New"),
            },
            set(
                StaticSegmentRecipient.objects.filter(
                    email="external@example.com"
                ).values_list("segment_id", "first_name")
            ),
        )
        self.assertFalse(ExternalRecipientConfirmation.objects.exists())

    def test_post_emptyFirstName_returns400(self, _: MagicMock):
        ExternalRecipient.objects.create(email="external@example.com", first_name="Old")

        response = self._post(first_name="  ", categories_registered_to={})

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            {"first_name": ["Dieses Feld darf nicht leer sein."]}, response.json()
        )

    def test_post_categoryNotAvailableForExternalRecipients_returns400(
        self, _: MagicMock
    ):
        ExternalRecipient.objects.create(email="external@example.com", first_name="Old")
        members_only = MailCategoryFactory.create(
            available_for_external_recipients=False
        )

        response = self._post(
            first_name="New", categories_registered_to={members_only.id: True}
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(StaticSegmentRecipient.objects.exists())

    def _post(self, first_name: str, categories_registered_to: dict[str, bool]):
        return self.client.post(
            reverse("core:subscription_management_external"),
            data={
                "token": "the_token",
                "first_name": first_name,
                "categories_registered_to": categories_registered_to,
            },
            content_type="application/json",
        )
