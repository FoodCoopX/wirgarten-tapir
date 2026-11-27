from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status

from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(
    SubscriptionManagementTokenSigner,
    "get_address",
    autospec=True,
    return_value="extra@example.com",
)
class TestSubscriptionManagementView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_tokenIsInvalidOrExpired_showsTheExpiredPage(
        self, mock_get_address: MagicMock
    ):
        mock_get_address.return_value = None

        response = self.client.get(self._build_url())

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTemplateUsed(
            response, "core/subscription_management_link_expired.html"
        )
        self.assertContains(
            response, reverse("core:subscription_management_link_request")
        )

    def test_get_addressIsAMainAddress_redirectsToTheMemberProfile(
        self, mock_get_address: MagicMock
    ):
        member = MemberFactory.create(email="main@example.com")
        mock_get_address.return_value = "main@example.com"

        response = self.client.get(self._build_url())

        self.assertRedirects(
            response,
            reverse("wirgarten:member_detail", args=[member.id]),
            fetch_redirect_response=False,
        )

    def test_get_addressIsNotAMainAddress_showsTheManagementPageForTheAddress(
        self, mock_get_address: MagicMock
    ):
        response = self.client.get(self._build_url())

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "core/subscription_management.html")
        self.assertContains(response, "extra@example.com")
        mock_get_address.assert_called_once_with(token="the_token")

    @staticmethod
    def _build_url() -> str:
        return reverse("core:subscription_management", args=["the_token"])
