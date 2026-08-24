from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True)
class TestMailingListEditView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[MockMailingListData(name="test")],
        )
        mailing_list = domain.lists[0]

        response = self.client.put(
            reverse("core:mailing_list_edit"),
            data={
                "name": "test@example.com",
                "advertised": True,
                "description": "Description after",
            },
            content_type="application/json",
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        mailing_list.settings.save.assert_not_called()

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_post_mailingListsDisabled_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[MockMailingListData(name="test")],
        )
        mailing_list = domain.lists[0]

        response = self.client.put(
            reverse("core:mailing_list_edit"),
            data={
                "name": "test@example.com",
                "advertised": True,
                "description": "Description after",
            },
            content_type="application/json",
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        mailing_list.settings.save.assert_not_called()

    def test_post_default_listUpdated(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="test",
                    description="Description before",
                    advertised=False,
                )
            ],
        )
        mailing_list = domain.lists[0]

        response = self.client.put(
            reverse("core:mailing_list_edit"),
            data={
                "name": "test@example.com",
                "advertised": True,
                "description": "Description after",
            },
            content_type="application/json",
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )

        self.assertTrue(mailing_list.settings["advertised"])
        self.assertEqual("Description after", mailing_list.settings["description"])
        mailing_list.settings.save.assert_called_once_with()

    def test_post_listNotFound_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[MockMailingListData(name="test")],
        )
        mailing_list = domain.lists[0]

        response = self.client.put(
            reverse("core:mailing_list_edit"),
            data={
                "name": "other@example.com",
                "advertised": True,
                "description": "Description after",
            },
            content_type="application/json",
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )
        mailing_list.settings.save.assert_not_called()
