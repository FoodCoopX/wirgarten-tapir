from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True)
class TestMailingListMemberSelfUnsubscribeView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_post_mailingListsDisabled_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[MockMailingListData(name="test_name", advertised=True)],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_unsubscribe"),
            data={"member_id": member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        mailing_list.unsubscribe.assert_not_called()

    def test_post_loggedInUserIsTargetMember_unsubscribes(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name",
                    advertised=True,
                    confirmed_recipients=[member.email],
                )
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_unsubscribe"),
            data={"member_id": member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        mailing_list.unsubscribe.assert_called_once_with(
            email=member.email,
            pre_confirmed=True,
            pre_approved=True,
        )

    def test_post_loggedInUserIsAdmin_unsubscribes(self):
        logged_in_user = MemberFactory.create(is_superuser=True)
        target_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_user)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name",
                    advertised=True,
                    confirmed_recipients=[target_member.email],
                )
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_unsubscribe"),
            data={"member_id": target_member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        mailing_list.unsubscribe.assert_called_once_with(
            email=target_member.email,
            pre_confirmed=True,
            pre_approved=True,
        )

    def test_post_loggedInUserIsNotTargetMember_returns403(self):
        logged_in_user = MemberFactory.create(is_superuser=False)
        target_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_user)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name",
                    advertised=True,
                    confirmed_recipients=[target_member.email],
                )
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_unsubscribe"),
            data={"member_id": target_member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        mailing_list.unsubscribe.assert_not_called()

    def test_post_memberIsNotSubscribed_returns400(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name",
                    advertised=True,
                    confirmed_recipients=[],
                )
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_unsubscribe"),
            data={"member_id": member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        mailing_list.unsubscribe.assert_not_called()
