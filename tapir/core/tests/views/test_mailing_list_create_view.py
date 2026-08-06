from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.tests.mailman_test_helper import (
    MailmanTestHelper,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMailingListCreateView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        post_data = {
            "name": "test_name",
            "description": "test_description",
            "advertised": False,
        }
        response = self.client.post(reverse("core:mailing_list_create"), data=post_data)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_post_mailingListsDisabled_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        post_data = {
            "name": "test_name",
            "description": "test_description",
            "advertised": False,
        }
        response = self.client.post(reverse("core:mailing_list_create"), data=post_data)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

    def test_post_default_callsCreateList(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        domain = MailmanTestHelper.mock_domain(test=self, mailing_list_datas=[])

        post_data = {
            "name": "test_name",
            "description": "test_description",
            "advertised": False,
        }
        response = self.client.post(reverse("core:mailing_list_create"), data=post_data)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        domain.create_list.assert_called_once_with(list_name="test_name")

        response_content = response.json()
        self.assertEqual(
            {
                "name": "test_name@example.com",
                "nb_recipients": 0,
                "description": "test_description",
                "advertised": False,
            },
            response_content,
        )

    @override_settings(EMAIL_HOST="example.com")
    def test_post_inputListNameContainsDomain_callsCreateListWithoutDomain(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        domain = MailmanTestHelper.mock_domain(test=self, mailing_list_datas=[])

        post_data = {
            "name": "prefix",
            "description": "test_description",
            "advertised": False,
        }
        response = self.client.post(reverse("core:mailing_list_create"), data=post_data)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        domain.create_list.assert_called_once_with(list_name="prefix")

        response_content = response.json()
        self.assertEqual(
            {
                "name": "prefix@example.com",
                "nb_recipients": 0,
                "description": "test_description",
                "advertised": False,
            },
            response_content,
        )
