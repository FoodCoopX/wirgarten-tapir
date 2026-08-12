from tapir.generic_exports.models import CsvExport
from tapir.generic_exports.services.csv_templates.template_member_list_geng import (
    TemplateMemberListGeng,
)
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestTemplateMemberListGeng(TapirIntegrationTest):
    def test_createExports_default_createsCorrectExport(self):
        TemplateMemberListGeng.create_exports()

        export = CsvExport.objects.get()
        self.assertEqual(
            MemberSegmentProvider.SEGMENT_ID_ALL_MEMBERS,
            export.export_segment_id,
        )
        self.assertEqual(
            [
                MemberColumnProvider.COLUMN_ID_MEMBER_NUMBER,
                MemberColumnProvider.COLUMN_ID_LAST_NAME,
                MemberColumnProvider.COLUMN_ID_FIRST_NAME,
                MemberColumnProvider.COLUMN_ID_FULL_ADDRESS,
                MemberColumnProvider.COLUMN_ID_ADMISSION_DATE,
                MemberColumnProvider.COLUMN_ID_SHARE_QUANTITY,
                MemberColumnProvider.COLUMN_ID_SHARE_HISTORY,
                MemberColumnProvider.COLUMN_ID_TERMINATION_DATE,
            ],
            export.column_ids,
        )
