from unittest.mock import patch, Mock, call, ANY

from tapir.generic_exports.services.export_segment_manager import ExportSegmentManager
from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
from tapir.generic_exports.tests.factories import PdfExportFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberWithCoopSharesFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildContexts(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    @patch.object(PdfExportBuilder, "build_context_for_entry")
    def test_buildContexts_default_buildsContextOnlyForUsedColumns(
        self, mock_build_context_for_entry: Mock
    ):
        export = PdfExportFactory.create(
            export_segment_id="members.all",
            template="Test template {{member_last_name}} {{member_number}}",
        )
        mock_datetime = Mock()
        members = [
            MemberWithCoopSharesFactory.create(),
            MemberWithCoopSharesFactory.create(),
        ]

        PdfExportBuilder.build_contexts(export, mock_datetime)

        self.assertEqual(2, mock_build_context_for_entry.call_count)
        mock_build_context_for_entry.assert_has_calls(
            [
                call(
                    member,
                    ExportSegmentManager.get_segment_by_id("members.all"),
                    mock_datetime,
                    ["member_last_name", "member_number"],
                    cache=ANY,
                )
                for member in members
            ]
        )
