from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True)
class TestMailingListDeleteView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        list_name = "test_name"
        domain = MailmanTestHelper.mock_domain(
            test=self, mailing_list_datas=[MockMailingListData(name=list_name)]
        )
        mailing_list = domain.lists[0]

        url = reverse("core:mailing_list_delete")
        url = f"{url}?list_name={list_name}"
        response = self.client.delete(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        mailing_list.delete.assert_not_called()

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_post_mailingListsDisabled_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        list_name = "test_name"
        domain = MailmanTestHelper.mock_domain(
            test=self, mailing_list_datas=[MockMailingListData(name=list_name)]
        )
        mailing_list = domain.lists[0]

        url = reverse("core:mailing_list_delete")
        url = f"{url}?list_name={list_name}"
        response = self.client.delete(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )
        mailing_list.delete.assert_not_called()

    def test_post_default_listDeleted(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        list_name = "test_name"
        domain = MailmanTestHelper.mock_domain(
            test=self, mailing_list_datas=[MockMailingListData(name=list_name)]
        )
        mailing_list = domain.lists[0]

        url = reverse("core:mailing_list_delete")
        url = f"{url}?list_name={list_name}@example.com"
        response = self.client.delete(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )
        mailing_list.delete.assert_called_once_with()

    def test_post_listNotFound_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        list_name = "test_name"
        domain = MailmanTestHelper.mock_domain(
            test=self, mailing_list_datas=[MockMailingListData(name=list_name)]
        )
        mailing_list = domain.lists[0]

        url = reverse("core:mailing_list_delete")
        url = f"{url}?list_name=test_name2@example.com"
        response = self.client.delete(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )
        mailing_list.delete.assert_not_called()
