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
class TestMailingListHeldMessagesView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def build_url(self, list_name: str):
        url = reverse("core:mailing_list_held_messages")
        return f"{url}?list_name={list_name}"

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        MailmanTestHelper.mock_domain(
            test=self, mailing_list_datas=[MockMailingListData(name="list_a")]
        )

        response = self.client.get(self.build_url("list_a@example.com"))

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_get_mailingListsDisabled_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        MailmanTestHelper.mock_domain(
            test=self, mailing_list_datas=[MockMailingListData(name="list_a")]
        )

        response = self.client.get(self.build_url("list_a@example.com"))

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

    def test_get_mailingListDoesntExist_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        MailmanTestHelper.mock_domain(
            test=self, mailing_list_datas=[MockMailingListData(name="list_a")]
        )

        response = self.client.get(self.build_url("list_b@example.com"))

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )

    @override_settings(EMAIL_HOST="example.com")
    def test_get_default_returnsHeldMessagesSortedByHoldDate(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_a",
                    held_messages=[
                        MockHeldMessageData(
                            request_id=2,
                            sender="later@example.com",
                            subject="Later",
                            hold_date="2026-10-22T14:00:00",
                            msg="Subject: Later\n\nLater body\n",
                        ),
                        MockHeldMessageData(
                            request_id=1,
                            sender="earlier@example.com",
                            subject="Earlier",
                            reason="The message is not from a list member",
                            hold_date="2026-10-21T08:30:00",
                            msg=(
                                "Subject: Earlier\n"
                                "MIME-Version: 1.0\n"
                                'Content-Type: multipart/alternative; boundary="b"\n'
                                "\n"
                                "--b\n"
                                "Content-Type: text/plain\n"
                                "\n"
                                "Plain body\n"
                                "--b\n"
                                "Content-Type: text/html\n"
                                "\n"
                                "<p>HTML body</p>\n"
                                "--b--\n"
                            ),
                        ),
                    ],
                ),
            ],
        )

        response = self.client.get(self.build_url("list_a@example.com"))

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        self.assertEqual(
            [
                {
                    "request_id": 1,
                    "sender": "earlier@example.com",
                    "subject": "Earlier",
                    "reason": "The message is not from a list member",
                    "hold_date": "2026-10-21T10:30:00+02:00",
                    "body": "Plain body",
                },
                {
                    "request_id": 2,
                    "sender": "later@example.com",
                    "subject": "Later",
                    "reason": "The message comes from a moderated member",
                    "hold_date": "2026-10-22T16:00:00+02:00",
                    "body": "Later body\n",
                },
            ],
            response.json(),
        )
