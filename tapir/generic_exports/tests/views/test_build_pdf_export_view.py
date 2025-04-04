import datetime
import json
from unittest.mock import patch, Mock

from django.urls import reverse

from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
from tapir.generic_exports.tests.factories import PdfExportFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildPdfExportView(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

    @patch.object(PdfExportBuilder, "create_exported_files")
    def test_buildPdfExportView_default_returnsCorrectData(
        self, mock_create_exported_files: Mock
    ):
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)
        export = PdfExportFactory.create()
        reference_datetime = datetime.datetime(2024, 5, 27, 10, 48)

        mock_exported_file = Mock()
        mock_exported_file.id = "test id"
        mock_create_exported_files.return_value = [mock_exported_file]

        base_url = reverse("generic_exports:build_pdf_export")
        response = self.client.get(
            f"{base_url}?pdf_export_id={export.id}&reference_datetime={reference_datetime.isoformat()}"
        )

        self.assertStatusCode(response, 200)
        mock_create_exported_files.assert_called_once_with(export, reference_datetime)

        self.assertEqual(
            reverse("wirgarten:exported_files_download", args=["test id"]),
            json.loads(response.content.decode()),
        )

    def test_buildPdfExportView_loggedInAsNormalUser_returns403(self):
        user = MemberFactory.create()
        self.client.force_login(user)

        response = self.client.get(reverse("generic_exports:build_pdf_export"))

        self.assertStatusCode(response, 403)
