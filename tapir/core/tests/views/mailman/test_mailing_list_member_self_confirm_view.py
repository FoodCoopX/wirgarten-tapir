from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMailingListMemberSelfConfirmView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_post_mailingListsDisabled_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name", unconfirmed_recipients=[member.email]
                )
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_confirm"),
            data={"member_id": member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        mailing_list.accept_request.assert_not_called()

    def test_post_loggedInUserIsTargetMember_confirms(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name", unconfirmed_recipients=[member.email]
                )
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_confirm"),
            data={"member_id": member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        mailing_list.accept_request.assert_called_once_with(
            request_id=mailing_list.requests[0]["token"]
        )

    def test_post_loggedInUserIsAdmin_confirms(self):
        logged_in_user = MemberFactory.create(is_superuser=True)
        target_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_user)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name", unconfirmed_recipients=[target_member.email]
                )
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_confirm"),
            data={"member_id": target_member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        mailing_list.accept_request.assert_called_once_with(
            request_id=mailing_list.requests[0]["token"]
        )

    def test_post_loggedInUserIsNotTargetMember_returns403(self):
        logged_in_user = MemberFactory.create(is_superuser=False)
        target_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_user)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test_name", unconfirmed_recipients=[target_member.email]
                )
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_confirm"),
            data={"member_id": target_member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        mailing_list.accept_request.assert_not_called()

    def test_post_noInvitationPending_returns400(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="test_name", unconfirmed_recipients=[])
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.post(
            reverse("core:member_self_confirm"),
            data={"member_id": member.id, "list_name": "test_name@example.com"},
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        mailing_list.accept_request.assert_not_called()
