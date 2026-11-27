from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.models import MemberExtraEmailSubscriptionsChangedLogEntry
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True, MAILING_LIST_DOMAIN="example.com")
@patch.object(
    SubscriptionManagementTokenSigner,
    "get_address",
    autospec=True,
    return_value="address@example.com",
)
class TestSubscriptionManagementMailingListUnsubscribeApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_addressIsAConfirmedExtra_appliesAndLogsOnTheMember(
        self, _: MagicMock
    ):
        self.mailing_list = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list", confirmed_recipients=["address@example.com"]
                )
            ],
        ).lists[0]
        extra_email = MemberExtraEmailFactory.create(
            email="address@example.com", confirmed_on=timezone.now()
        )

        response = self.client.post(
            reverse("core:subscription_management_mailing_list_unsubscribe"),
            data={"token": "the_token", "list_name": "list@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.mailing_list.unsubscribe.assert_called_once_with(
            email="address@example.com", pre_confirmed=True, pre_approved=True
        )
        log_entry = MemberExtraEmailSubscriptionsChangedLogEntry.objects.get()
        self.assertEqual(["Liste list@example.com: abgemeldet"], log_entry.changes)
        self.assertEqual(extra_email.member_id, log_entry.user_id)
