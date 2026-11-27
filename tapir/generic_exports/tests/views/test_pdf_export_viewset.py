from django.urls import reverse

from tapir.generic_exports.tests.factories import PdfExportFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPdfExportViewset(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

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

    def test_pdfExportViewset_patchEmailRecipients_storesNormalisedAddresses(self):
        self.client.force_login(MemberFactory(is_superuser=True))
        export = PdfExportFactory.create()

        response = self.client.patch(
            reverse("generic_exports:pdf_exports-detail", args=[export.id]),
            data={"email_recipients": [" First@Example.com", "second@example.com"]},
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        export.refresh_from_db()
        self.assertEqual(
            ["first@example.com", "second@example.com"], export.email_recipients
        )
