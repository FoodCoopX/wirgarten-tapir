import json
from unittest.mock import patch

from django.urls import reverse

from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.generic_exports.services.export_segment_manager import (
    ExportSegment,
    ExportSegmentColumn,
    ExportSegmentManager,
)
from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.generic_exports.tests.factories import CsvExportFactory, PdfExportFactory
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetExportSegmentsView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

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

    def test_get_association_keepsSavedCooperativeSegments(self):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self.client.force_login(MemberFactory.create(is_superuser=True))
        url = reverse("generic_exports:export_segments")
        segments = {
            segment.id: segment
            for segment in MemberSegmentProvider.get_member_segments()
        }
        csv_segment = "members.with_contract_since_more_than_one_year_but_no_coop_share"
        pdf_segment = "members.with_cancelled_shares_in_previous_year"

        with patch.object(ExportSegmentManager, "registered_export_segments", segments):
            response = self.client.get(url)
            self.assertStatusCode(response, 200)
            segment_ids = {segment["id"] for segment in response.json()}
            self.assertIn(MemberSegmentProvider.SEGMENT_ID_ALL_MEMBERS, segment_ids)
            self.assertNotIn(csv_segment, segment_ids)
            self.assertNotIn(pdf_segment, segment_ids)

            CsvExportFactory.create(export_segment_id=csv_segment)
            PdfExportFactory.create(export_segment_id=pdf_segment)

            response = self.client.get(url)
            self.assertStatusCode(response, 200)
            segment_ids = {segment["id"] for segment in response.json()}
            self.assertIn(csv_segment, segment_ids)
            self.assertIn(pdf_segment, segment_ids)

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
