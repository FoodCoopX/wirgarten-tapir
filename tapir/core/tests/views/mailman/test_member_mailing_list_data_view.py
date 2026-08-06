from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberMailingListDataView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_memberGetsOwnData_returns200(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        MailmanTestHelper.mock_domain(test=self, mailing_list_datas=[])

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_memberGetsOtherMemberData_returns403(self):
        logged_in_user = MemberFactory.create(is_superuser=False)
        target_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_user)

        MailmanTestHelper.mock_domain(test=self, mailing_list_datas=[])

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={target_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_get_mailingListsAreDisabled_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        MailmanTestHelper.mock_domain(test=self, mailing_list_datas=[])

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_adminGetsOtherMemberData_returns200(self):
        logged_in_user = MemberFactory.create(is_superuser=True)
        target_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_user)

        MailmanTestHelper.mock_domain(test=self, mailing_list_datas=[])

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={target_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_listIsAdvertised_resultContainsList(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[MockMailingListData(name="test_name", advertised=True)],
        )

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(
            {
                "available_lists": [
                    {
                        "advertised": True,
                        "description": "",
                        "name": "test_name@example.com",
                        "nb_recipients": 0,
                    }
                ],
                "subscribed_lists": [],
                "waiting_for_confirmation_lists": [],
            },
            response_content,
        )

    def test_get_listIsNotAdvertised_resultDoesntContainsList(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="test_name", advertised=False)
            ],
        )

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(
            {
                "available_lists": [],
                "subscribed_lists": [],
                "waiting_for_confirmation_lists": [],
            },
            response_content,
        )

    def test_get_memberIsSubscribedToList_subscriptionsContainsList(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name",
                    advertised=True,
                    confirmed_recipients=[member.email],
                )
            ],
        )

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(
            {
                "available_lists": [
                    {
                        "advertised": True,
                        "description": "",
                        "name": "test_name@example.com",
                        "nb_recipients": 1,
                    }
                ],
                "subscribed_lists": ["test_name@example.com"],
                "waiting_for_confirmation_lists": [],
            },
            response_content,
        )

    def test_get_memberIsInvitedToList_invitationsContainsList(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name",
                    advertised=True,
                    unconfirmed_recipients=[member.email],
                )
            ],
        )

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(
            {
                "available_lists": [
                    {
                        "advertised": True,
                        "description": "",
                        "name": "test_name@example.com",
                        "nb_recipients": 1,
                    }
                ],
                "subscribed_lists": [],
                "waiting_for_confirmation_lists": ["test_name@example.com"],
            },
            response_content,
        )

    def test_get_listIsNotAdvertisedButMemberIsSubscribed_resultContainsList(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name",
                    advertised=False,
                    confirmed_recipients=[member.email],
                )
            ],
        )

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(
            {
                "available_lists": [
                    {
                        "advertised": False,
                        "description": "",
                        "name": "test_name@example.com",
                        "nb_recipients": 1,
                    }
                ],
                "subscribed_lists": ["test_name@example.com"],
                "waiting_for_confirmation_lists": [],
            },
            response_content,
        )

    def test_get_listIsNotAdvertisedButMemberIsInvited_resultContainsList(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name",
                    advertised=False,
                    unconfirmed_recipients=[member.email],
                )
            ],
        )

        url = reverse("core:member_mailing_list_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(
            {
                "available_lists": [
                    {
                        "advertised": False,
                        "description": "",
                        "name": "test_name@example.com",
                        "nb_recipients": 1,
                    }
                ],
                "subscribed_lists": [],
                "waiting_for_confirmation_lists": ["test_name@example.com"],
            },
            response_content,
        )
