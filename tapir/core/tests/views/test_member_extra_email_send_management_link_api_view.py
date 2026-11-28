from unittest.mock import ANY, MagicMock, patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.core.services.subscription_management_link_sender import (
    SubscriptionManagementLinkSender,
)
from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(SubscriptionManagementLinkSender, "send_link", autospec=True)
class TestMemberExtraEmailSendManagementLinkApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)

    def test_post_featureIsDisabled_returns400(self, mock_send_link: MagicMock):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False)
        extra_email = self._create_extra_email()
        self.client.force_login(extra_email.member)

        response = self._post(extra_email=extra_email)

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(["Diese Funktion ist ausgeschaltet."], response.json())
        mock_send_link.assert_not_called()

    def test_post_userIsAnotherMember_returns403(self, mock_send_link: MagicMock):
        extra_email = self._create_extra_email()
        self.client.force_login(MemberFactory.create())

        response = self._post(extra_email=extra_email)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        mock_send_link.assert_not_called()

    def test_post_extraIsNotConfirmed_returns400(self, mock_send_link: MagicMock):
        extra_email = self._create_extra_email(confirmed=False)
        self.client.force_login(extra_email.member)

        response = self._post(extra_email=extra_email)

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(["Diese Adresse ist noch nicht bestätigt"], response.json())
        mock_send_link.assert_not_called()

    def test_post_ownConfirmedExtra_sendsTheLinkToTheExtraAddress(
        self, mock_send_link: MagicMock
    ):
        extra_email = self._create_extra_email()
        self.client.force_login(extra_email.member)

        response = self._post(extra_email=extra_email)

        self.assertStatusCode(response, status.HTTP_200_OK)
        mock_send_link.assert_called_once_with(address="extra@example.com", cache=ANY)

    @staticmethod
    def _create_extra_email(confirmed: bool = True) -> MemberExtraEmail:
        return MemberExtraEmailFactory.create(
            email="extra@example.com",
            confirmed_on=timezone.now() if confirmed else None,
        )

    def _post(self, extra_email: MemberExtraEmail):
        return self.client.post(
            reverse("core:member_extra_email_send_management_link"),
            data={"extra_email_id": extra_email.id},
        )
