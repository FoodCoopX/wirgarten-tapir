from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True)
class TestMailingListRecipientListView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="list_a"),
            ],
        )

        url = reverse("core:mailing_list_recipient_list")
        url = f"{url}?list_name=list_a@example.com"
        response = self.client.get(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_get_mailingListsDisabled_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="list_a"),
            ],
        )

        url = reverse("core:mailing_list_recipient_list")
        url = f"{url}?list_name=list_a@example.com"
        response = self.client.get(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

    def test_get_mailingListDoesntExist_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="list_a"),
                MockMailingListData(name="list_b"),
            ],
        )

        url = reverse("core:mailing_list_recipient_list")
        url = f"{url}?list_name=list_c@example.com"
        response = self.client.get(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )

    def test_get_default_returnsCorrectContent(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        existing_member_1 = MemberFactory.create(email="member1@example.com")
        existing_member_2 = MemberFactory.create(email="member2@example.com")

        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_a",
                    confirmed_recipients=[
                        "member1@example.com",
                        "notmember1@example.com",
                    ],
                    unconfirmed_recipients=[
                        "member2@example.com",
                        "notmember2@example.com",
                    ],
                ),
                MockMailingListData(
                    name="list_b",
                    confirmed_recipients=["other@example.com"],
                ),
            ],
        )

        url = reverse("core:mailing_list_recipient_list")
        url = f"{url}?list_name=list_a@example.com"
        response = self.client.get(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )

        response_content = response.json()
        recipients_by_email = {
            recipient["address"]: recipient for recipient in response_content
        }

        self.assertEqual(
            {
                "member1@example.com": {
                    "address": "member1@example.com",
                    "user_confirmed": True,
                    "link_to_member_profile": reverse(
                        "wirgarten:member_detail",
                        kwargs={"pk": existing_member_1.id},
                    ),
                },
                "notmember1@example.com": {
                    "address": "notmember1@example.com",
                    "user_confirmed": True,
                    "link_to_member_profile": None,
                },
                "member2@example.com": {
                    "address": "member2@example.com",
                    "user_confirmed": False,
                    "link_to_member_profile": reverse(
                        "wirgarten:member_detail",
                        kwargs={"pk": existing_member_2.id},
                    ),
                },
                "notmember2@example.com": {
                    "address": "notmember2@example.com",
                    "user_confirmed": False,
                    "link_to_member_profile": None,
                },
            },
            recipients_by_email,
        )
