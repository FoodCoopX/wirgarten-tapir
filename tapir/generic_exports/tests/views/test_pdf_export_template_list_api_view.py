from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status

from tapir.generic_exports.services.pdf_export_template_manager import (
    PdfExportTemplateManager,
    TemplateData,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPdfExportTemplateListApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_normalUserTriesToGetList_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(reverse("generic_exports:pdf_export_templates"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    @patch.object(PdfExportTemplateManager, "get_templates", autospec=True)
    def test_get_default_returnsCorrectList(self, mock_get_templates: Mock):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        mock_get_templates.return_value = {
            "tid1": TemplateData(
                id="tid1",
                name="tname1",
                description="tdescription1",
                create_method=Mock(),
            ),
            "tid2": TemplateData(
                id="tid2",
                name="tname2",
                description="tdescription2",
                create_method=Mock(),
            ),
        }

        response = self.client.get(reverse("generic_exports:pdf_export_templates"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(2, len(response_content))

        self.assertIn(
            {"id": "tid1", "name": "tname1", "description": "tdescription1"},
            response_content,
        )
        self.assertIn(
            {"id": "tid2", "name": "tname2", "description": "tdescription2"},
            response_content,
        )
