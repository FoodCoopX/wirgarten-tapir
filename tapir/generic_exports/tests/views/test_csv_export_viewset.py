from django.urls import reverse

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCsvExportViewset(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_csvExportViewset_loggedInAsNormalUser_returns403(self):
        member = MemberFactory()
        self.client.force_login(member)

        response = self.client.get(reverse("generic_exports:csv_exports-list"))
        self.assertStatusCode(response, 403)

    def test_csvExportViewset_loggedInAsAdmin_returns200(self):
        member = MemberFactory(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("generic_exports:csv_exports-list"))
        self.assertStatusCode(response, 200)
