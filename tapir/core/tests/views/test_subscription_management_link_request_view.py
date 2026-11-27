from unittest.mock import ANY, MagicMock, patch

from django.urls import reverse
from rest_framework import status

from tapir.core.services.subscription_management_link_sender import (
    SubscriptionManagementLinkSender,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(SubscriptionManagementLinkSender, "send_link", autospec=True)
class TestSubscriptionManagementLinkRequestView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_default_showsTheForm(self, mock_send_link: MagicMock):
        response = self.client.get(reverse("core:subscription_management_link_request"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTemplateUsed(
            response, "core/subscription_management_link_request.html"
        )
        mock_send_link.assert_not_called()

    def test_post_validAddress_sendsTheLinkToTheNormalisedAddressAndRedirects(
        self, mock_send_link: MagicMock
    ):
        response = self.client.post(
            reverse("core:subscription_management_link_request"),
            data={"email": " Extra@Example.com "},
        )

        self.assertRedirects(
            response,
            reverse("core:subscription_management_link_requested"),
            fetch_redirect_response=False,
        )
        mock_send_link.assert_called_once_with(address="extra@example.com", cache=ANY)

    def test_post_addressRequestedWithinTheCooldown_sendsOnlyOnceButRedirectsBothTimes(
        self, mock_send_link: MagicMock
    ):
        for _ in range(2):
            response = self.client.post(
                reverse("core:subscription_management_link_request"),
                data={"email": "extra@example.com"},
            )

            self.assertRedirects(
                response,
                reverse("core:subscription_management_link_requested"),
                fetch_redirect_response=False,
            )
        mock_send_link.assert_called_once_with(address="extra@example.com", cache=ANY)

    def test_post_otherAddressWithinTheCooldown_sendsToBoth(
        self, mock_send_link: MagicMock
    ):
        for address in ["first@example.com", "second@example.com"]:
            self.client.post(
                reverse("core:subscription_management_link_request"),
                data={"email": address},
            )

        self.assertEqual(
            ["first@example.com", "second@example.com"],
            [call.kwargs["address"] for call in mock_send_link.call_args_list],
        )

    def test_post_invalidAddress_showsTheFormAgainWithoutSending(
        self, mock_send_link: MagicMock
    ):
        response = self.client.post(
            reverse("core:subscription_management_link_request"),
            data={"email": "not an address"},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTemplateUsed(
            response, "core/subscription_management_link_request.html"
        )
        mock_send_link.assert_not_called()
