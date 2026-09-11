from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMandateReferencePreviewApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_normalMemberTriesToGetPreview_returns403(self):
        admin = MemberFactory.create(is_superuser=False)
        self.client.force_login(admin)

        url = reverse("payments:mandate_reference_preview")
        response = self.client.get(f"{url}?pattern={{vorname}}-{{zufall}}")

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_validPattern_returnsPreviewsForBothPreviewMembers(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        url = reverse("payments:mandate_reference_preview")
        response = self.client.get(
            f"{url}?pattern={{vorname}}-{{nachname}}-{{mitgliedsnummer_kurz}}"
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual("", response_content["error"])
        self.assertEqual(2, len(response_content["previews"]))
        self.assertEqual(
            {
                "John Doe #17": "JOHN-DOE-17",
                "Maximilian Mustermann #123456": "MAXIM-MUSTE-123456",
            },
            response_content["previews"],
        )
