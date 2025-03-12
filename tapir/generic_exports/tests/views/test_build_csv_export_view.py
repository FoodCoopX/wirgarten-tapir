import datetime
import json
from unittest.mock import patch, Mock

from django.urls import reverse

from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.tests.factories import CsvExportFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetExportSegmentsView(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

    @patch.object(CsvExportBuilder, "create_exported_file")
    def test_getExportSegmentsView_default_returnsCorrectData(
        self, mock_create_exported_file: Mock
    ):
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)
        export = CsvExportFactory.create()
        mock_file = Mock()
        mock_create_exported_file.return_value = mock_file
        mock_file.name = "Test name"
        mock_file.file.decode.return_value = "Test file content"
        reference_datetime = datetime.datetime(2024, 5, 27, 10, 48)

        base_url = reverse("generic_exports:build_csv_export")
        response = self.client.get(
            f"{base_url}?csv_export_id={export.id}&reference_datetime={reference_datetime.isoformat()}"
        )

        self.assertStatusCode(response, 200)
        mock_create_exported_file.assert_called_once_with(export, reference_datetime)
        mock_file.file.decode.assert_called_once_with("utf-8")

        result = json.loads(response.content)
        expected = {"file_name": "Test name", "file_as_string": "Test file content"}
        self.assertEqual(expected, result)

    def test_getExportSegmentsView_loggedInAsNormalUser_returns403(self):
        user = MemberFactory.create()
        self.client.force_login(user)

        response = self.client.get(reverse("generic_exports:build_csv_export"))

        self.assertStatusCode(response, 403)
