from tapir.utils.services.data_import_service import (
    IMPORT_TYPES,
    STATUS_CREATED,
    STATUS_ERROR,
    STATUS_SKIPPED,
    DataImportService,
)
from tapir.utils.services.tabular_file_reader import TabularData
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

HEADERS = ["Nr", "Vorname", "Nachname", "Mailadresse", "consent_sepa"]


def member_row(number: int, **overrides) -> dict[str, str]:
    row = {
        "Nr": str(number),
        "Vorname": "Erika",
        "Nachname": f"Musterfrau {number}",
        "Mailadresse": f"erika{number}@example.org",
        "consent_sepa": "2024-03-01",
    }
    row.update(overrides)
    return row


class TestDataImportService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def run_members(self, rows, dry_run, headers=HEADERS, update_existing=False):
        return DataImportService.run(
            import_type=IMPORT_TYPES["members"],
            data=TabularData(headers=headers, rows=rows),
            update_existing=update_existing,
            dry_run=dry_run,
        )

    def test_run_dryRun_reportsRowsAndSavesNothing(self):
        result = self.run_members([member_row(1), member_row(2)], dry_run=True)

        self.assertEqual(
            [STATUS_CREATED, STATUS_CREATED], [r.status for r in result.rows]
        )
        self.assertEqual("1 Erika Musterfrau 1", result.rows[0].label)
        self.assertEqual(2, result.rows[0].line)
        self.assertTrue(result.can_be_applied)
        self.assertFalse(Member.objects.exists())

    def test_run_apply_createsMembersAndSkipsThemTheSecondTime(self):
        self.run_members([member_row(1), member_row(2)], dry_run=False)
        self.assertEqual(
            {1, 2}, set(Member.objects.values_list("member_no", flat=True))
        )

        result = self.run_members([member_row(1)], dry_run=False)

        self.assertEqual([STATUS_SKIPPED], [r.status for r in result.rows])

    def test_run_oneRowFails_reportsTheRowAndSavesNothing(self):
        result = self.run_members(
            [member_row(1), member_row(2, Abholort="Gibt es nicht")],
            dry_run=False,
            headers=HEADERS + ["Abholort"],
        )

        self.assertEqual(
            [STATUS_CREATED, STATUS_ERROR], [r.status for r in result.rows]
        )
        self.assertIn("Gibt es nicht", result.rows[1].message)
        self.assertFalse(result.can_be_applied)
        self.assertFalse(Member.objects.exists())

    def test_run_missingRequiredColumn_importsNothing(self):
        result = self.run_members(
            [member_row(1)],
            dry_run=False,
            headers=["Nr", "Vorname", "Nachname", "Extra"],
        )

        self.assertEqual(["Mailadresse", "consent_sepa"], result.missing_columns)
        self.assertEqual(["Extra"], result.unknown_columns)
        self.assertEqual([], result.rows)
        self.assertFalse(Member.objects.exists())

    def test_run_emptyRows_areIgnored(self):
        result = self.run_members(
            [member_row(1), {header: "" for header in HEADERS}], dry_run=True
        )

        self.assertEqual(1, len(result.rows))

    def test_buildTemplate_containsAllColumnsAndTheExampleRow(self):
        import io

        from openpyxl import load_workbook

        import_type = IMPORT_TYPES["shares"]
        sheet = load_workbook(
            io.BytesIO(DataImportService.build_template(import_type))
        ).active

        self.assertEqual(list(import_type.columns), [cell.value for cell in sheet[1]])
        self.assertEqual("Z", sheet["B2"].value)
