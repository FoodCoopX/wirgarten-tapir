from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.core.services.former_member_address_provider import (
    FormerMemberAddressProvider,
)
from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.mail.models import ExternalRecipient
from tapir.wirgarten.models import MemberExtraEmailSubscriptionsChangedLogEntry
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(
    FormerMemberAddressProvider,
    "is_former_member_address",
    autospec=True,
    return_value=False,
)
@override_settings(MAILING_LISTS_ENABLED=True, MAILING_LIST_DOMAIN="example.com")
@patch.object(
    SubscriptionManagementTokenSigner,
    "get_address",
    autospec=True,
    return_value="address@example.com",
)
class TestSubscriptionManagementMailingListSubscribeApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        self.mailing_list = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[MockMailingListData(name="list", advertised=True)],
        ).lists[0]

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_post_mailingListsDisabled_returns403(self, _: MagicMock, __: MagicMock):
        response = self._post()

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.mailing_list.subscribe.assert_not_called()

    def test_post_tokenIsInvalid_returns403(
        self, mock_get_address: MagicMock, _: MagicMock
    ):
        mock_get_address.return_value = None

        response = self._post()

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.mailing_list.subscribe.assert_not_called()

    def test_post_addressIsAConfirmedExtra_subscribesAndLogsOnTheMember(
        self, _: MagicMock, __: MagicMock
    ):
        extra_email = MemberExtraEmailFactory.create(
            email="address@example.com", confirmed_on=timezone.now()
        )

        response = self._post()

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.mailing_list.subscribe.assert_called_once_with(
            address="address@example.com",
            invitation=False,
            pre_confirmed=True,
            pre_verified=True,
        )
        log_entry = MemberExtraEmailSubscriptionsChangedLogEntry.objects.get()
        self.assertEqual(["Liste list@example.com: angemeldet"], log_entry.changes)
        self.assertEqual(extra_email.member_id, log_entry.user_id)

    def test_post_addressIsAnExternalRecipient_subscribesWithoutLog(
        self, _: MagicMock, __: MagicMock
    ):
        ExternalRecipient.objects.create(email="address@example.com", first_name="E")

        response = self._post()

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.mailing_list.subscribe.assert_called_once()
        self.assertFalse(MemberExtraEmailSubscriptionsChangedLogEntry.objects.exists())

    def test_post_addressIsNeitherAConfirmedExtraNorAnExternalRecipient_returns400(
        self, _: MagicMock, __: MagicMock
    ):
        MemberExtraEmailFactory.create(email="address@example.com", confirmed_on=None)

        response = self._post()

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            ["Diese Adresse kann sich nicht selbst bei einer Liste anmelden"],
            response.json(),
        )
        self.mailing_list.subscribe.assert_not_called()

    def _post(self):
        return self.client.post(
            reverse("core:subscription_management_mailing_list_subscribe"),
            data={"token": "the_token", "list_name": "list@example.com"},
        )

    def test_post_addressBelongsToAFormerMember_returns400(
        self, _: MagicMock, mock_is_former_member_address: MagicMock
    ):
        mock_is_former_member_address.return_value = True
        MemberExtraEmailFactory.create(
            email="address@example.com", confirmed_on=timezone.now()
        )

        response = self._post()

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            [
                "Diese Adresse gehört zu einem ehemaligen Mitglied und kann keiner Mailing-Liste beitreten"
            ],
            response.json(),
        )
        self.mailing_list.subscribe.assert_not_called()
