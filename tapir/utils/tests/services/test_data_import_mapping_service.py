from tapir.utils.services.data_import_mapping_service import (
    CELL_INVALID,
    CELL_NEUTRAL,
    CELL_VALID,
    CELL_WARN,
    DataImportMappingService,
)
from tapir.wirgarten.models import CoopShareTransaction, Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildSemanticFields(TapirIntegrationTest):
    def test_singleType_oneFieldPerColumn(self):
        fields = DataImportMappingService.build_semantic_fields(["members"])

        by_key = {f.key: f for f in fields}
        self.assertIn("member_no", by_key)
        self.assertEqual({"members": "Nr"}, by_key["member_no"].import_columns)
        self.assertTrue(by_key["member_no"].required)
        self.assertIn("members:Vorname", by_key)

    def test_combinedTypes_memberNumberIsOneSharedField(self):
        fields = DataImportMappingService.build_semantic_fields(
            ["members", "shares", "subscriptions"]
        )

        member_no_fields = [f for f in fields if f.key == "member_no"]
        self.assertEqual(1, len(member_no_fields))
        field = member_no_fields[0]
        self.assertEqual(
            {
                "members": "Nr",
                "shares": "Mitgliedsnummer",
                "subscriptions": "Mitgliedernummer",
            },
            field.import_columns,
        )
        self.assertTrue(field.required)
        # every other column still has its own, type-specific field
        keys = {f.key for f in fields}
        self.assertIn("members:Vorname", keys)
        self.assertIn("shares:Datum", keys)
        self.assertIn("subscriptions:product", keys)
        # no column should appear twice
        self.assertEqual(len(keys), len(fields))


class TestNormalizeHeader(TapirIntegrationTest):
    def test_toleratesCaseWhitespaceAndPunctuation(self):
        self.assertEqual(
            DataImportMappingService.normalize_header("Nr"),
            DataImportMappingService.normalize_header(" nr. "),
        )
        self.assertEqual(
            DataImportMappingService.normalize_header("consent_sepa"),
            DataImportMappingService.normalize_header("Consent-SEPA"),
        )
        self.assertEqual(
            DataImportMappingService.normalize_header("Straße"),
            DataImportMappingService.normalize_header("Strasse"),
        )


class TestAutoMap(TapirIntegrationTest):
    def test_exactImporterHeaders_alwaysMap(self):
        fields = DataImportMappingService.build_semantic_fields(["members"])
        headers = ["Nr", "Vorname", "Nachname", "Mailadresse", "consent_sepa"]

        mapping = DataImportMappingService.auto_map(headers, fields)

        self.assertEqual(
            {
                "Nr": "member_no",
                "Vorname": "members:Vorname",
                "Nachname": "members:Nachname",
                "Mailadresse": "members:Mailadresse",
                "consent_sepa": "members:consent_sepa",
            },
            mapping,
        )

    def test_synonymAndPunctuationTolerantHeaders_map(self):
        fields = DataImportMappingService.build_semantic_fields(["members"])
        headers = ["Mitgliedsnummer", "First Name", "Last Name", "E-Mail"]

        mapping = DataImportMappingService.auto_map(headers, fields)

        self.assertEqual("member_no", mapping["Mitgliedsnummer"])
        self.assertEqual("members:Vorname", mapping["First Name"])
        self.assertEqual("members:Nachname", mapping["Last Name"])
        self.assertEqual("members:Mailadresse", mapping["E-Mail"])

    def test_combinedTypes_sharedMemberNumberColumn_mapsOnce(self):
        fields = DataImportMappingService.build_semantic_fields(["members", "shares"])
        headers = ["Mitgliedsnummer", "Vorname", "Nachname", "Mailadresse"]

        mapping = DataImportMappingService.auto_map(headers, fields)

        self.assertEqual("member_no", mapping["Mitgliedsnummer"])
        # only one source column feeds the shared member number target
        self.assertEqual(1, sum(1 for key in mapping.values() if key == "member_no"))

    def test_eachTarget_mapsAtMostOneColumn(self):
        fields = DataImportMappingService.build_semantic_fields(["members"])
        # two columns that could both match "Nr" after normalisation
        headers = ["Nr", "Mitgliedsnummer"]

        mapping = DataImportMappingService.auto_map(headers, fields)

        self.assertEqual(1, sum(1 for key in mapping.values() if key == "member_no"))


class TestMappingValidation(TapirIntegrationTest):
    def test_missingRequiredFields_detected(self):
        fields = DataImportMappingService.build_semantic_fields(["members"])
        mapping = {"Nr": "member_no", "Vorname": "members:Vorname"}

        missing = DataImportMappingService.missing_required_fields(mapping, fields)

        missing_keys = {f.key for f in missing}
        self.assertIn("members:Mailadresse", missing_keys)
        self.assertIn("members:consent_sepa", missing_keys)
        self.assertNotIn("member_no", missing_keys)

    def test_duplicateTargets_detected(self):
        mapping = {"Nr": "member_no", "Mitgliedsnummer": "member_no"}

        duplicates = DataImportMappingService.duplicate_targets(mapping)

        self.assertEqual({"member_no"}, duplicates)


HEADERS = [
    "Mitgliedsnummer",
    "Vorname",
    "Nachname",
    "Mailadresse",
    "consent_sepa",
    "Bewegungsart (Z,Ü,K)",
    "Datum",
    "Anzahl Anteile",
]

MAPPING = {
    "Mitgliedsnummer": "member_no",
    "Vorname": "members:Vorname",
    "Nachname": "members:Nachname",
    "Mailadresse": "members:Mailadresse",
    "consent_sepa": "members:consent_sepa",
    "Bewegungsart (Z,Ü,K)": "shares:Bewegungsart (Z,Ü,K)",
    "Datum": "shares:Datum",
    "Anzahl Anteile": "shares:Anzahl Anteile",
}


def combined_row(number: int, **overrides) -> dict[str, str]:
    row = {
        "Mitgliedsnummer": str(number),
        "Vorname": "Erika",
        "Nachname": f"Musterfrau {number}",
        "Mailadresse": f"erika{number}@example.org",
        "consent_sepa": "01.03.2024",
        "Bewegungsart (Z,Ü,K)": "Z",
        "Datum": "01.03.2024",
        "Anzahl Anteile": "2",
    }
    row.update(overrides)
    return row


class TestEvaluateAndApply(TapirIntegrationTest):
    """Combined members + shares, with the member number coming from a single shared column."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self.selected_type_keys = ["members", "shares"]
        self.semantic_fields = DataImportMappingService.build_semantic_fields(
            self.selected_type_keys
        )

    def test_validRow_isGreenAndDryRunSucceeds(self):
        rows = [combined_row(1)]

        outcomes = DataImportMappingService.evaluate(
            selected_type_keys=self.selected_type_keys,
            semantic_fields=self.semantic_fields,
            mapping=MAPPING,
            headers=HEADERS,
            raw_rows=rows,
            update_existing=False,
        )

        self.assertEqual(1, len(outcomes))
        outcome = outcomes[0]
        self.assertTrue(outcome.valid)
        self.assertEqual([], outcome.messages)
        for header in HEADERS:
            self.assertEqual(CELL_VALID, outcome.cell_states[header])
        # dry run never writes anything
        self.assertFalse(Member.objects.exists())

    def test_requiredCellEmpty_isRedAndRowInvalid(self):
        rows = [combined_row(1, Mailadresse="")]

        outcomes = DataImportMappingService.evaluate(
            selected_type_keys=self.selected_type_keys,
            semantic_fields=self.semantic_fields,
            mapping=MAPPING,
            headers=HEADERS,
            raw_rows=rows,
            update_existing=False,
        )

        outcome = outcomes[0]
        self.assertFalse(outcome.valid)
        self.assertEqual(CELL_INVALID, outcome.cell_states["Mailadresse"])
        self.assertTrue(any("Mailadresse" in message for message in outcome.messages))

    def test_malformedDateCell_isRed(self):
        rows = [combined_row(1, Datum="not-a-date")]

        outcomes = DataImportMappingService.evaluate(
            selected_type_keys=self.selected_type_keys,
            semantic_fields=self.semantic_fields,
            mapping=MAPPING,
            headers=HEADERS,
            raw_rows=rows,
            update_existing=False,
        )

        outcome = outcomes[0]
        self.assertFalse(outcome.valid)
        self.assertEqual(CELL_INVALID, outcome.cell_states["Datum"])

    def test_optionalColumnEntirelyEmpty_isNeutral(self):
        headers = HEADERS + ["Übertragungspartner"]
        mapping = dict(MAPPING)
        mapping["Übertragungspartner"] = "shares:Übertragungspartner"
        rows = [combined_row(1, **{"Übertragungspartner": ""})]

        outcomes = DataImportMappingService.evaluate(
            selected_type_keys=self.selected_type_keys,
            semantic_fields=self.semantic_fields,
            mapping=mapping,
            headers=headers,
            raw_rows=rows,
            update_existing=False,
        )

        self.assertEqual(CELL_NEUTRAL, outcomes[0].cell_states["Übertragungspartner"])

    def test_optionalCellEmptyButColumnHasOtherValues_isWarn(self):
        headers = HEADERS + ["Übertragungspartner"]
        mapping = dict(MAPPING)
        mapping["Übertragungspartner"] = "shares:Übertragungspartner"
        rows = [
            combined_row(1, **{"Übertragungspartner": ""}),
            combined_row(2, **{"Übertragungspartner": "3"}),
        ]

        outcomes = DataImportMappingService.evaluate(
            selected_type_keys=self.selected_type_keys,
            semantic_fields=self.semantic_fields,
            mapping=mapping,
            headers=headers,
            raw_rows=rows,
            update_existing=False,
        )

        self.assertEqual(CELL_WARN, outcomes[0].cell_states["Übertragungspartner"])

    def test_businessError_rowInvalidButFormatValidCellsStayGreen(self):
        # Member 999 does not exist: ShareImporter raises a business error that is not
        # attributable to a single cell, but the member number cell itself is format-valid.
        rows = [combined_row(999)]
        shares_only_headers = [
            "Mitgliedsnummer",
            "Bewegungsart (Z,Ü,K)",
            "Datum",
            "Anzahl Anteile",
        ]
        shares_only_mapping = {
            header: MAPPING[header] for header in shares_only_headers
        }

        outcomes = DataImportMappingService.evaluate(
            selected_type_keys=["shares"],
            semantic_fields=DataImportMappingService.build_semantic_fields(["shares"]),
            mapping=shares_only_mapping,
            headers=shares_only_headers,
            raw_rows=[{h: rows[0][h] for h in shares_only_headers}],
            update_existing=False,
        )

        outcome = outcomes[0]
        self.assertFalse(outcome.valid)
        self.assertEqual(1, len(outcome.messages))
        self.assertIn("999", outcome.messages[0])
        self.assertEqual(CELL_VALID, outcome.cell_states["Mitgliedsnummer"])

    def test_applyRows_onlySelectedRowsAreImported(self):
        rows = [combined_row(1), combined_row(2)]

        count = DataImportMappingService.apply_rows(
            selected_type_keys=self.selected_type_keys,
            semantic_fields=self.semantic_fields,
            mapping=MAPPING,
            raw_rows=rows,
            row_indices=[0],
            update_existing=False,
        )

        self.assertEqual(1, count)
        self.assertEqual({1}, set(Member.objects.values_list("member_no", flat=True)))
        self.assertTrue(
            CoopShareTransaction.objects.filter(member__member_no=1).exists()
        )

    def test_applyRows_oneRowFails_rollsBackAllSelectedRows(self):
        rows = [combined_row(1), combined_row(2, Datum="not-a-date")]

        with self.assertRaises(RuntimeError):
            DataImportMappingService.apply_rows(
                selected_type_keys=self.selected_type_keys,
                semantic_fields=self.semantic_fields,
                mapping=MAPPING,
                raw_rows=rows,
                row_indices=[0, 1],
                update_existing=False,
            )

        self.assertFalse(Member.objects.exists())
        self.assertFalse(CoopShareTransaction.objects.exists())
