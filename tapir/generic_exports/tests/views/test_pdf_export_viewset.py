from django.urls import reverse

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPdfExportViewset(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

    def test_pdfExportViewset_loggedInAsNormalUser_returns403(self):
        member = MemberFactory()
        self.client.force_login(member)

        response = self.client.get(reverse("generic_exports:pdf_exports-list"))
        self.assertStatusCode(response, 403)

    def test_pdfExportViewset_loggedInAsAdmin_returns200(self):
        member = MemberFactory(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("generic_exports:pdf_exports-list"))
        self.assertStatusCode(response, 200)
