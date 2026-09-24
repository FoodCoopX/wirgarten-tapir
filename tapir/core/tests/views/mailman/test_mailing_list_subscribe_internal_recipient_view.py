from unittest.mock import Mock

from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.services.mailman.mailing_list_provider import MailingListProvider
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True)
class TestMailingListSubscribeInternalRecipientView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        member = MemberFactory.create(email="member@example.com")

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="list_a"),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_b@example.com",
            "member_id": member.id,
        }
        response = self.client.post(
            reverse("core:mailing_list_subscribe_internal"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        for mailing_list in domain.lists:
            mailing_list.subscribe.assert_not_called()

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_post_mailingListsDisabled_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        member = MemberFactory.create(email="member@example.com")

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="list_a"),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_b@example.com",
            "member_id": member.id,
        }
        response = self.client.post(
            reverse("core:mailing_list_subscribe_internal"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        for mailing_list in domain.lists:
            mailing_list.subscribe.assert_not_called()

    def test_post_mailingListDoesntExist_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        member = MemberFactory.create(email="member@example.com")

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="list_a"),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_c@example.com",
            "member_id": member.id,
        }
        response = self.client.post(
            reverse("core:mailing_list_subscribe_internal"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )
        for mailing_list in domain.lists:
            mailing_list.subscribe.assert_not_called()

    def test_post_memberDoesntExist_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        MemberFactory.create(email="member@example.com")

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="list_a"),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_b@example.com",
            "member_id": "invalid_id",
        }
        response = self.client.post(
            reverse("core:mailing_list_subscribe_internal"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )
        for mailing_list in domain.lists:
            mailing_list.subscribe.assert_not_called()

    def test_post_default_callsSubscribe(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        member = MemberFactory.create(email="member@example.com")

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="list_a"),
                MockMailingListData(name="list_b"),
            ],
        )

        post_data = {
            "list_name": "list_b@example.com",
            "member_id": member.id,
        }
        response = self.client.post(
            reverse("core:mailing_list_subscribe_internal"), data=post_data
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        mailing_list_b: Mock = MailingListProvider.get_list_by_name_or_404(
            list_name="list_b@example.com", cache={}
        )
        mailing_list_b.subscribe.assert_called_once_with(
            address="member@example.com", invitation=True
        )
        mailing_list_a: Mock = MailingListProvider.get_list_by_name_or_404(
            list_name="list_a@example.com", cache={}
        )
        mailing_list_a.subscribe.assert_not_called()
