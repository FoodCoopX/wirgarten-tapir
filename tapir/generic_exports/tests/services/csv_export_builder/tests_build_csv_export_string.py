import datetime

from icecream import ic

from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.tests.factories import CsvExportFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberWithCoopSharesFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCreateExportedFile(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

    def test_buildCsvExportString_default_returnsCorrectString(self):
        export = CsvExportFactory.create(
            export_segment_id="members.all",
            column_ids=["member.first_name", "member.last_name"],
            separator=":",
        )
        MemberWithCoopSharesFactory.create(first_name="FN1", last_name="LN1")
        MemberWithCoopSharesFactory.create(first_name="FN2", last_name="LN2")

        result = CsvExportBuilder.build_csv_export_string(
            csv_export=export,
            reference_datetime=datetime.datetime(
                year=2024, month=3, day=5, hour=12, minute=17
            ),
        )
        expected = "Vorname:Nachname\r\nFN1:LN1\r\nFN2:LN2\r\n"
        ic(expected, result)
        self.assertEqual(expected, result)
