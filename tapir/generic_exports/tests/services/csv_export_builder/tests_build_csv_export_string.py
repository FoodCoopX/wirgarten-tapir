import datetime

from icecream import ic

from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.tests.factories import CsvExportFactory
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberWithCoopSharesFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildCsvExportString(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

    def test_buildCsvExportString_default_returnsCorrectString(self):
        export = CsvExportFactory.create(
            export_segment_id="members.all",
            column_ids=["member_first_name", "member_last_name"],
            separator=":",
            custom_column_names=["test_custom_1", "test_custom_2"],
        )
        MemberWithCoopSharesFactory.create(first_name="FN1", last_name="LN1")
        MemberWithCoopSharesFactory.create(first_name="FN2", last_name="LN2")

        ic(
            [
                [member.id, member.first_name, member.last_name]
                for member in Member.objects.all()
            ]
        )

        result = CsvExportBuilder.build_csv_export_string(
            csv_export=export,
            reference_datetime=datetime.datetime(
                year=2024, month=3, day=5, hour=12, minute=17
            ),
        )
        expected = "test_custom_1:test_custom_2\r\nFN1:LN1\r\nFN2:LN2\r\n"
        self.assertEqual(expected, result)

    def test_buildCsvExportString_containsAnEmptyColumn_returnsCorrectString(self):
        export = CsvExportFactory.create(
            export_segment_id="members.all",
            column_ids=["member_first_name", "", "member_last_name"],
            separator=":",
            custom_column_names=["test_custom_1", "test_empty", "test_custom_2"],
        )
        MemberWithCoopSharesFactory.create(first_name="FN1", last_name="LN1")
        MemberWithCoopSharesFactory.create(first_name="FN2", last_name="LN2")

        ic(
            [
                [member.id, member.first_name, member.last_name]
                for member in Member.objects.all()
            ]
        )

        result = CsvExportBuilder.build_csv_export_string(
            csv_export=export,
            reference_datetime=datetime.datetime(
                year=2024, month=3, day=5, hour=12, minute=17
            ),
        )
        expected = "test_custom_1:test_empty:test_custom_2\r\nFN1::LN1\r\nFN2::LN2\r\n"
        self.assertEqual(expected, result)
