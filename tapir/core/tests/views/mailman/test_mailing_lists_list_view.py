from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMailingListListView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(reverse("core:mailing_list_list"))

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_get_mailingListsDisabled_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(reverse("core:mailing_list_list"))

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

    @override_settings(EMAIL_HOST="example.com")
    def test_get_default_returnsCorrectList(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="list_A",
                    confirmed_recipients=["1", "2", "3"],
                    unconfirmed_recipients=["4", "5"],
                    description="description A",
                    advertised=True,
                ),
                MockMailingListData(
                    name="list_B",
                    confirmed_recipients=["6", "7"],
                    unconfirmed_recipients=[],
                    advertised=False,
                ),
            ],
        )

        response = self.client.get(reverse("core:mailing_list_list"))

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )

        response_content = response.json()
        self.assertEqual(
            [
                {
                    "name": "list_A@example.com",
                    "nb_recipients": 5,
                    "description": "description A",
                    "advertised": True,
                },
                {
                    "name": "list_B@example.com",
                    "nb_recipients": 2,
                    "description": "",
                    "advertised": False,
                },
            ],
            response_content,
        )
