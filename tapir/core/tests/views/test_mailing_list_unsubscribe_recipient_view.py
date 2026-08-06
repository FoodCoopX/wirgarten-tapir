from unittest.mock import Mock

from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.services.mailman.mailing_list_provider import MailingListProvider
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMailingListUnsubscribeRecipientView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_a", unconfirmed_recipients=["foo@example.com"]
                ),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_a@example.com",
            "address": "foo@example.com",
        }
        response = self.client.post(
            reverse("core:mailing_list_unsubscribe"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        for mailing_list in domain.lists:
            mailing_list.subscribe.assert_not_called()

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_post_mailingListsDisabled_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_a", unconfirmed_recipients=["foo@example.com"]
                ),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_a@example.com",
            "address": "foo@example.com",
        }
        response = self.client.post(
            reverse("core:mailing_list_unsubscribe"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        for mailing_list in domain.lists:
            mailing_list.subscribe.assert_not_called()

    def test_post_mailingListDoesntExist_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_a", confirmed_recipients=["foo@example.com"]
                ),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "invalid@example.com",
            "address": "foo@example.com",
        }
        response = self.client.post(
            reverse("core:mailing_list_unsubscribe"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )
        for mailing_list in domain.lists:
            mailing_list.unsubscribe.assert_not_called()
            mailing_list.discard_request.assert_not_called()

    def test_post_addressIsNotInList_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_a", confirmed_recipients=["foo@example.com"]
                ),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_a@example.com",
            "address": "bar@example.com",
        }
        response = self.client.post(
            reverse("core:mailing_list_unsubscribe"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )
        for mailing_list in domain.lists:
            mailing_list.unsubscribe.assert_not_called()
            mailing_list.discard_request.assert_not_called()

    def test_post_memberWasConfirmed_callsUnsubscribe(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_a", confirmed_recipients=["foo@example.com"]
                ),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_a@example.com",
            "address": "foo@example.com",
        }
        response = self.client.post(
            reverse("core:mailing_list_unsubscribe"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        cache = {}
        mailing_list_a: Mock = MailingListProvider.get_list_by_name_or_404(
            list_name="list_a@example.com", cache=cache
        )
        mailing_list_a.unsubscribe.assert_called_once_with(
            email="foo@example.com", pre_confirmed=True
        )
        mailing_list_a.discard_request.assert_not_called()
        mailing_list_b: Mock = MailingListProvider.get_list_by_name_or_404(
            list_name="list_b@example.com", cache=cache
        )
        mailing_list_b.unsubscribe.assert_not_called()
        mailing_list_b.discard_request.assert_not_called()

    def test_post_memberWasNotConfirmed_callsDiscardRequest(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_a", unconfirmed_recipients=["foo@example.com"]
                ),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_a@example.com",
            "address": "foo@example.com",
        }
        response = self.client.post(
            reverse("core:mailing_list_unsubscribe"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        cache = {}
        mailing_list_a: Mock = MailingListProvider.get_list_by_name_or_404(
            list_name="list_a@example.com", cache=cache
        )
        mailing_list_a.unsubscribe.assert_not_called()
        mailing_list_a.discard_request.assert_called_once_with(
            request_id=mailing_list_a.requests[0]["token"]
        )
        mailing_list_b: Mock = MailingListProvider.get_list_by_name_or_404(
            list_name="list_b@example.com", cache=cache
        )
        mailing_list_b.unsubscribe.assert_not_called()
        mailing_list_b.discard_request.assert_not_called()
