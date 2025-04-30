from tapir.generic_exports.services.export_segment_manager import ExportSegmentManager
from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestBuildContextForEntry(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_buildContextForEntry_default_buildsContextWithOnlyUsedColumns(self):
        member = MemberFactory(member_no=1234, first_name="John")
        segment = ExportSegmentManager.get_segment_by_id("members.all")

        result = PdfExportBuilder.build_context_for_entry(
            member, segment, get_now(), ["member_number", "member_first_name"]
        )

        self.assertEqual({"member_number": "1234", "member_first_name": "John"}, result)
