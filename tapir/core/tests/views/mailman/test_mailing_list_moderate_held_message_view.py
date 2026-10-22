from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.tests.mailman_test_helper import (
    MailmanTestHelper,
    MockHeldMessageData,
    MockMailingListData,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True)
class TestMailingListModerateHeldMessageView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def mock_list_with_held_messages(self):
        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_a",
                    held_messages=[
                        MockHeldMessageData(request_id=1),
                        MockHeldMessageData(request_id=2),
                    ],
                ),
            ],
        )
        return domain.lists[0]

    def post(self, list_name: str, request_id: int, moderation_action: str):
        return self.client.post(
            reverse("core:mailing_list_moderate_held_message"),
            data={
                "list_name": list_name,
                "request_id": request_id,
                "moderation_action": moderation_action,
            },
        )

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        mailing_list = self.mock_list_with_held_messages()

        response = self.post("list_a@example.com", 1, "accept")

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        mailing_list.moderate_message.assert_not_called()

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_post_mailingListsDisabled_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        mailing_list = self.mock_list_with_held_messages()

        response = self.post("list_a@example.com", 1, "accept")

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        mailing_list.moderate_message.assert_not_called()

    def test_post_invalidAction_returns400(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        mailing_list = self.mock_list_with_held_messages()

        response = self.post("list_a@example.com", 1, "defer")

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_400_BAD_REQUEST
        )
        mailing_list.moderate_message.assert_not_called()

    def test_post_messageNotFound_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        mailing_list = self.mock_list_with_held_messages()

        response = self.post("list_a@example.com", 3, "accept")

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )
        mailing_list.moderate_message.assert_called_once_with(3, "accept")

    def test_post_accept_callsModerateOnCorrectMessage(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        mailing_list = self.mock_list_with_held_messages()

        response = self.post("list_a@example.com", 2, "accept")

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        mailing_list.moderate_message.assert_called_once_with(2, "accept")

    def test_post_reject_callsModerateOnCorrectMessage(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        mailing_list = self.mock_list_with_held_messages()

        response = self.post("list_a@example.com", 1, "reject")

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        mailing_list.moderate_message.assert_called_once_with(1, "reject")

    def test_post_discard_callsModerateOnCorrectMessage(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        mailing_list = self.mock_list_with_held_messages()

        response = self.post("list_a@example.com", 2, "discard")

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        mailing_list.moderate_message.assert_called_once_with(2, "discard")
