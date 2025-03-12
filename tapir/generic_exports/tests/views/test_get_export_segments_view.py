import json

from django.urls import reverse

from tapir.generic_exports.services.export_segment_manager import (
    ExportSegment,
    ExportSegmentColumn,
    ExportSegmentManager,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetExportSegmentsView(TapirIntegrationTest):

    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

    def test_getExportSegmentsView_default_returnsCorrectData(self):
        ExportSegmentManager.registered_export_segments = {}
        for segment in self.get_test_segments():
            ExportSegmentManager.register_segment(segment)

        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)

        response = self.client.get(reverse("generic_exports:export_segments"))

        self.assertStatusCode(response, 200)

        result = json.loads(response.content)
        expected = [
            {
                "id": "test_segment_1",
                "display_name": "Test name 1",
                "description": "Test description 1",
                "columns": [
                    {
                        "id": "test_column_1",
                        "display_name": "Test column 1",
                        "description": "Test description column 1",
                    },
                    {
                        "id": "test_column_2",
                        "display_name": "Test column 2",
                        "description": "Test description column 2",
                    },
                ],
            },
            {
                "id": "test_segment_2",
                "display_name": "Test name 2",
                "description": "Test description 2",
                "columns": [
                    {
                        "id": "test_column_1",
                        "display_name": "Test column 1",
                        "description": "Test description column 1",
                    },
                    {
                        "id": "test_column_2",
                        "display_name": "Test column 2",
                        "description": "Test description column 2",
                    },
                ],
            },
        ]

        self.assertEqual(expected, result)

    def test_getExportSegmentsView_loggedInAsNormalUser_returns403(self):
        user = MemberFactory.create()
        self.client.force_login(user)

        response = self.client.get(reverse("generic_exports:export_segments"))

        self.assertStatusCode(response, 403)

    def get_test_segments(self):
        return [
            ExportSegment(
                id="test_segment_1",
                display_name="Test name 1",
                description="Test description 1",
                get_queryset=lambda _: Member.objects.all(),
                get_available_columns=self.get_test_columns,
            ),
            ExportSegment(
                id="test_segment_2",
                display_name="Test name 2",
                description="Test description 2",
                get_queryset=lambda _: Member.objects.all(),
                get_available_columns=self.get_test_columns,
            ),
        ]

    @staticmethod
    def get_test_columns():
        return [
            ExportSegmentColumn(
                id="test_column_1",
                display_name="Test column 1",
                description="Test description column 1",
                get_value=lambda _, __: "test1",
            ),
            ExportSegmentColumn(
                id="test_column_2",
                display_name="Test column 2",
                description="Test description column 2",
                get_value=lambda _, __: "test2",
            ),
        ]
