from unittest.mock import ANY, MagicMock, patch

from django.urls import reverse
from rest_framework import status

from tapir.core.services.mailman.mailing_list_unsubscriber import (
    MailingListUnsubscriber,
)
from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.mail.models import ExternalRecipient, StaticSegmentRecipient
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(MailingListUnsubscriber, "unsubscribe_if_address_unused", autospec=True)
@patch.object(
    SubscriptionManagementTokenSigner,
    "get_address",
    autospec=True,
    return_value="external@example.com",
)
class TestSubscriptionManagementExternalApiViewDelete(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_delete_tokenIsInvalid_returns403(
        self, mock_get_address: MagicMock, mock_unsubscribe_if_address_unused: MagicMock
    ):
        mock_get_address.return_value = None
        ExternalRecipient.objects.create(email="external@example.com", first_name="E")

        response = self._delete()

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertTrue(ExternalRecipient.objects.exists())
        mock_unsubscribe_if_address_unused.assert_not_called()

    def test_delete_default_deletesTheRecipientAndItsPublicCategoryRowsThenUnsubscribes(
        self, _: MagicMock, mock_unsubscribe_if_address_unused: MagicMock
    ):
        ExternalRecipient.objects.create(email="external@example.com", first_name="E")
        public_category = MailCategoryFactory.create()
        members_only = MailCategoryFactory.create(
            available_for_external_recipients=False
        )
        for category in [public_category, members_only]:
            StaticSegmentRecipient.objects.create(
                segment=category.static_segment, email="external@example.com"
            )

        with self.captureOnCommitCallbacks(execute=True):
            response = self._delete()

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(ExternalRecipient.objects.exists())
        self.assertEqual(
            [members_only.static_segment_id],
            list(StaticSegmentRecipient.objects.values_list("segment_id", flat=True)),
        )
        mock_unsubscribe_if_address_unused.assert_called_once_with(
            email="external@example.com", cache=ANY
        )

    def _delete(self):
        return self.client.delete(
            reverse("core:subscription_management_external") + "?token=the_token"
        )
