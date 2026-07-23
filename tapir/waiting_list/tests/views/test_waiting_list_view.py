from django.urls import reverse

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestWaitingListView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_waitingListView_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self.client.get(reverse("waiting_list:list"))

        self.assertStatusCode(response, 403)

    def test_waitingListView_loggedInAsAdmin_returns200(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("waiting_list:list"))

        self.assertEqual(response.status_code, 200)
