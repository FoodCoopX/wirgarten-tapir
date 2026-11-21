from tapir.utils.services.data_import_mapping_service import (
    CELL_INVALID,
    CELL_DROPPED,
    CELL_DEFAULT,
    CELL_NEUTRAL,
    CELL_VALID,
    CELL_WARN,
    DataImportMappingService,
)
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
)
from tapir.wirgarten.models import (
    CoopShareTransaction,
    Member,
    MemberPickupLocation,
    PickupLocation,
    Product,
    Subscription,
    PickupLocationCapability,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
    ProductPriceFactory,
    ProductTypeFactory,
    MandateReferenceFactory,
)
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
                "Mailadresse": "email",
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
        self.assertEqual("email", mapping["E-Mail"])

    def test_autoMap_vetragsdatumHeader_mapsToVertragsbeginn(self):
        fields = DataImportMappingService.build_semantic_fields(["subscriptions"])

        mapping = DataImportMappingService.auto_map(["Vetragsdatum"], fields)

        self.assertEqual("subscriptions:Vertragsbeginn", mapping["Vetragsdatum"])

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
        self.assertIn("email", missing_keys)
        self.assertIn("members:consent_sepa", missing_keys)
        self.assertNotIn("member_no", missing_keys)

    def test_missingRequiredFields_withDefault_areSatisfied(self):
        fields = DataImportMappingService.build_semantic_fields(["members"])
        mapping = {"Nr": "member_no", "Vorname": "members:Vorname"}
        missing = DataImportMappingService.missing_required_fields(
            mapping,
            fields,
            {
                "email": "default@example.org",
                "members:consent_sepa": "2024-01-01",
            },
        )
        self.assertIn("email", {f.key for f in missing})

    def test_missingRequiredFields_sepaConsentFromContractStart_isSatisfied(self):
        fields = DataImportMappingService.build_semantic_fields(
            ["members", "subscriptions"], cache={}
        )
        mapping = {"Start": "subscriptions:Vertragsbeginn"}

        missing = DataImportMappingService.missing_required_fields(
            mapping, fields, {}, {"sepa_consent_from_contract_start": True}
        )

        self.assertNotIn("members:consent_sepa", {f.key for f in missing})

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
    "Mailadresse": "email",
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

    def test_emptyMappedCell_withDefault_usesDefaultAndIsMarked(self):
        rows = [combined_row(1, Mailadresse="")]
        defaults = {"email": "default@example.org"}
        outcomes = DataImportMappingService.evaluate(
            self.selected_type_keys,
            self.semantic_fields,
            MAPPING,
            HEADERS,
            rows,
            False,
            defaults,
        )
        self.assertTrue(outcomes[0].valid)
        self.assertEqual(CELL_DEFAULT, outcomes[0].cell_states["Mailadresse"])
        mapped = DataImportMappingService.build_mapped_row(
            rows[0], MAPPING, self.semantic_fields, "members", defaults
        )
        self.assertEqual("default@example.org", mapped["Mailadresse"])

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

    def test_computeRowCellStates_validIban_isValidAndNormalized(self):
        fields = DataImportMappingService.build_semantic_fields(["members"])
        field = next(field for field in fields if field.key == "members:IBAN")

        states, errors, dropped = DataImportMappingService.compute_row_cell_states(
            {"IBAN": "DE89 3704 0044 0532 0130 00"},
            ["IBAN"],
            {"IBAN": field.key},
            {field.key: field},
            {"IBAN": True},
        )

        self.assertEqual(CELL_VALID, states["IBAN"])
        self.assertEqual([], errors)
        self.assertEqual([], dropped)
        mapped_row = DataImportMappingService.build_mapped_row(
            {"IBAN": "DE89 3704 0044 0532 0130 00"},
            {"IBAN": field.key},
            fields,
            "members",
        )
        self.assertEqual("DE89370400440532013000", mapped_row["IBAN"])

    def test_evaluate_invalidIban_rowStaysValidAndIbanIsDropped(self):
        headers = HEADERS + ["IBAN"]
        mapping = dict(MAPPING)
        mapping["IBAN"] = "members:IBAN"
        rows = [combined_row(1, IBAN="not-an-iban")]

        outcomes = DataImportMappingService.evaluate(
            selected_type_keys=self.selected_type_keys,
            semantic_fields=self.semantic_fields,
            mapping=mapping,
            headers=headers,
            raw_rows=rows,
            update_existing=False,
        )

        outcome = outcomes[0]
        self.assertTrue(outcome.valid)
        self.assertEqual(CELL_DROPPED, outcome.cell_states["IBAN"])
        self.assertEqual(
            ['IBAN "not-an-iban" ist ungültig, Mitglied wird ohne IBAN übernommen'],
            outcome.messages,
        )
        mapped_row = DataImportMappingService.build_mapped_row(
            rows[0], mapping, self.semantic_fields, "members"
        )
        self.assertNotIn("IBAN", mapped_row)

    def test_applyRows_updateWithInvalidIban_keepsExistingIban(self):
        headers = [
            "Mitgliedsnummer",
            "Vorname",
            "Nachname",
            "Mailadresse",
            "consent_sepa",
            "IBAN",
        ]
        mapping = {header: MAPPING.get(header, "members:IBAN") for header in headers}
        semantic_fields = DataImportMappingService.build_semantic_fields(["members"])

        def apply(iban: str, update_existing: bool):
            row = combined_row(1, IBAN=iban)
            DataImportMappingService.apply_rows(
                selected_type_keys=["members"],
                semantic_fields=semantic_fields,
                mapping=mapping,
                raw_rows=[{header: row[header] for header in headers}],
                row_indices=[0],
                update_existing=update_existing,
            )

        apply("DE89 3704 0044 0532 0130 00", update_existing=False)
        apply("not-an-iban", update_existing=True)

        self.assertEqual("DE89370400440532013000", Member.objects.get(member_no=1).iban)

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


class TestRowStatus(TapirIntegrationTest):
    MEMBER_HEADERS = ["Mitgliedsnummer", "Vorname", "Nachname", "Mailadresse"]

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self.fields = DataImportMappingService.build_semantic_fields(["members"])
        self.mapping = {header: MAPPING[header] for header in self.MEMBER_HEADERS}
        self.mapping["consent_sepa"] = "members:consent_sepa"
        self.headers = self.MEMBER_HEADERS + ["consent_sepa"]

    def row(self, **overrides):
        row = combined_row(1, **overrides)
        return {header: row[header] for header in self.headers}

    def evaluate(self, row, update_existing, options=None):
        return DataImportMappingService.evaluate(
            ["members"],
            self.fields,
            self.mapping,
            self.headers,
            [row],
            update_existing,
            options=options,
        )[0]

    def import_member(self):
        DataImportMappingService.apply_rows(
            ["members"], self.fields, self.mapping, [self.row()], [0], False
        )

    def test_evaluate_newMember_isNewAndEditable(self):
        outcome = self.evaluate(self.row(), update_existing=False)

        self.assertEqual("new", outcome.status)
        self.assertTrue(outcome.editable)

    def test_evaluate_sameDataWithUpdate_isUnchangedButEditable(self):
        self.import_member()

        outcome = self.evaluate(self.row(), update_existing=True)

        self.assertEqual("unchanged", outcome.status)
        self.assertTrue(outcome.editable)

    def test_evaluate_changedDataWithoutUpdate_isExistingAndNotEditable(self):
        self.import_member()

        outcome = self.evaluate(self.row(Nachname="Neu"), update_existing=False)

        self.assertEqual("existing", outcome.status)
        self.assertFalse(outcome.editable)

    def test_evaluate_changedLastNameWithUpdate_isChangedWithOldValue(self):
        self.import_member()

        outcome = self.evaluate(self.row(Nachname="Neu"), update_existing=True)

        self.assertEqual("changed", outcome.status)
        self.assertEqual({"Nachname": "Musterfrau 1"}, outcome.old_values)
        self.assertEqual("Musterfrau 1", Member.objects.get(member_no=1).last_name)

    def test_buildMappedRow_emptyAccountOwnerWithOption_usesFullName(self):
        mapping = dict(self.mapping, Kontoinhaber="members:Kontoinhaber")

        mapped = DataImportMappingService.build_mapped_row(
            dict(self.row(), Kontoinhaber=""),
            mapping,
            self.fields,
            "members",
            options={"account_owner_from_name": True},
        )

        self.assertEqual("Erika Musterfrau 1", mapped["Kontoinhaber"])

    def test_rowStatus_existingMemberWithNewSubscriptionWithoutUpdate_isChanged(
        self,
    ):
        status = DataImportMappingService.row_status(
            True,
            [MEMBER_IMPORT_STATUS_SKIPPED, MEMBER_IMPORT_STATUS_CREATED],
            True,
            False,
        )

        self.assertEqual("changed", status)

    def test_rowStatus_invalid_isInvalid(self):
        self.assertEqual(
            "invalid",
            DataImportMappingService.row_status(
                False, [MEMBER_IMPORT_STATUS_CREATED], False, True
            ),
        )


class TestPickupLocationMapping(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self.fields = DataImportMappingService.build_semantic_fields(["members"])
        self.headers = [
            "Nr",
            "Vorname",
            "Nachname",
            "Mailadresse",
            "consent_sepa",
            "Abholort",
        ]
        self.mapping = {
            "Nr": "member_no",
            "Vorname": "members:Vorname",
            "Nachname": "members:Nachname",
            "Mailadresse": "email",
            "consent_sepa": "members:consent_sepa",
            "Abholort": "members:Abholort",
        }
        self.row = {
            "Nr": "101",
            "Vorname": "Erika",
            "Nachname": "Musterfrau",
            "Mailadresse": "erika@example.org",
            "consent_sepa": "01.03.2024",
            "Abholort": "  Zentrum   Nord ",
        }

    def test_applyRows_existingMappingWithDifferentSpelling_assignsExistingLocation(
        self,
    ):
        location = PickupLocationFactory(name="Zentrum Nord")
        DataImportMappingService.apply_rows(
            ["members"],
            self.fields,
            self.mapping,
            [self.row],
            [0],
            False,
            pickup_location_mapping={"Zentrum Nord": f"existing:{location.pk}"},
        )
        member = Member.objects.get(member_no=101)
        self.assertEqual(
            location,
            MemberPickupLocation.objects.get(member=member).pickup_location,
        )

    def test_evaluateAndApplyRows_createMapping_dryRunPersistsNothingAndApplyCreatesCapabilities(
        self,
    ):
        product_type = ProductTypeFactory()
        outcomes = DataImportMappingService.evaluate(
            ["members"],
            self.fields,
            self.mapping,
            self.headers,
            [self.row],
            False,
            pickup_location_mapping={"Zentrum Nord": "create"},
        )
        self.assertTrue(outcomes[0].valid, outcomes[0].messages)
        self.assertFalse(PickupLocation.objects.filter(name="Zentrum Nord").exists())
        DataImportMappingService.apply_rows(
            ["members"],
            self.fields,
            self.mapping,
            [self.row],
            [0],
            False,
            pickup_location_mapping={"Zentrum Nord": "create"},
        )
        location = PickupLocation.objects.get(name="Zentrum Nord")
        self.assertTrue(
            PickupLocationCapability.objects.filter(
                pickup_location=location, product_type=product_type, max_capacity=None
            ).exists()
        )

    def test_pickupMappingUsedByRows_valueOnlyInUnselectedRow_isExcluded(self):
        other_row = {**self.row, "Nr": "102", "Abholort": "Hof Süd"}
        result = DataImportMappingService.pickup_mapping_used_by_rows(
            [self.row, other_row],
            [0],
            self.mapping,
            {"Zentrum Nord": "create", "Hof Süd": "create"},
        )
        self.assertEqual({"Zentrum Nord": "create"}, result)

    def test_evaluateAndApplyRows_skipMapping_rowValidAndNoPickupLocation(self):
        outcomes = DataImportMappingService.evaluate(
            ["members"],
            self.fields,
            self.mapping,
            self.headers,
            [self.row],
            False,
            pickup_location_mapping={"Zentrum Nord": "skip"},
        )
        self.assertTrue(outcomes[0].valid)
        self.assertEqual("dropped", outcomes[0].cell_states["Abholort"])
        DataImportMappingService.apply_rows(
            ["members"],
            self.fields,
            self.mapping,
            [self.row],
            [0],
            False,
            pickup_location_mapping={"Zentrum Nord": "skip"},
        )
        member = Member.objects.get(member_no=101)
        self.assertFalse(MemberPickupLocation.objects.filter(member=member).exists())


class TestSharedEmailField(TapirIntegrationTest):
    def test_buildSemanticFields_membersAndSubscriptions_shareEmailField(self):
        fields = DataImportMappingService.build_semantic_fields(
            ["members", "subscriptions"]
        )
        email_fields = [field for field in fields if field.key == "email"]
        self.assertEqual(1, len(email_fields))
        self.assertEqual(
            {"members": "Mailadresse", "subscriptions": "Email"},
            email_fields[0].import_columns,
        )
        mapping = {"Mail": "email"}
        row = {"Mail": "erika@example.org"}
        member_row = DataImportMappingService.build_mapped_row(
            row, mapping, fields, "members"
        )
        subscription_row = DataImportMappingService.build_mapped_row(
            row, mapping, fields, "subscriptions"
        )
        self.assertEqual("erika@example.org", member_row["Mailadresse"])
        self.assertEqual("erika@example.org", subscription_row["Email"])


class TestProductQuantityMapping(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.period = GrowingPeriodFactory()
        cls.product = ProductFactory(name="Käse")
        ProductPriceFactory(product=cls.product, valid_from=cls.period.start_date)
        cls.member = MemberFactory(member_no=101)

    def test_buildImportRows_productQuantityTwo_createsSubscriptionRow(self):
        fields = DataImportMappingService.build_semantic_fields(
            ["subscriptions"], cache={}
        )
        product_key = f"product:{self.product.pk}"
        mapping = {
            "Nr": "member_no",
            "Start": "subscriptions:Vertragsbeginn",
            "Ende": "subscriptions:Vertragsende",
            "Käse": product_key,
        }
        rows = DataImportMappingService.build_import_rows(
            {
                "Nr": "101",
                "Start": self.period.start_date.isoformat(),
                "Ende": self.period.end_date.isoformat(),
                "Käse": "2",
            },
            0,
            ["subscriptions"],
            fields,
            mapping,
            {},
            {},
            {},
            {},
        )
        self.assertEqual("2", rows["subscriptions"][0]["Quantity"])
        self.assertEqual("Käse", rows["subscriptions"][0]["product"])

    def test_computeRowCellStates_quantityZeroOrEmpty_isNotInvalid(self):
        fields = DataImportMappingService.build_semantic_fields(
            ["subscriptions"], cache={}
        )
        field = next(
            field for field in fields if field.product_id == str(self.product.pk)
        )
        mapping = {"Käse": field.key}
        for value in ("0", ""):
            states, errors, _ = DataImportMappingService.compute_row_cell_states(
                {"Käse": value}, ["Käse"], mapping, {field.key: field}, {"Käse": True}
            )
            self.assertNotEqual(CELL_INVALID, states["Käse"])
            self.assertEqual([], errors)

    def test_computeRowCellStates_quantityDecimal_isInvalid(self):
        fields = DataImportMappingService.build_semantic_fields(
            ["subscriptions"], cache={}
        )
        field = next(
            field for field in fields if field.product_id == str(self.product.pk)
        )
        states, errors, _ = DataImportMappingService.compute_row_cell_states(
            {"Käse": "1,5"},
            ["Käse"],
            {"Käse": field.key},
            {field.key: field},
            {"Käse": True},
        )
        self.assertEqual(CELL_INVALID, states["Käse"])
        self.assertTrue(any("nur ganze Zahlen möglich" in error for error in errors))

    def test_missingRequiredFields_productColumnMapped_doesNotRequireLongFormatFields(
        self,
    ):
        fields = DataImportMappingService.build_semantic_fields(
            ["subscriptions"], cache={}
        )
        product_key = f"product:{self.product.pk}"
        missing = DataImportMappingService.missing_required_fields(
            {"Käse": product_key}, fields
        )
        self.assertNotIn("subscriptions:product", {field.key for field in missing})
        self.assertNotIn("subscriptions:Quantity", {field.key for field in missing})

    def test_applyRows_productQuantityTwo_createsSubscription(self):
        fields = DataImportMappingService.build_semantic_fields(
            ["subscriptions"], cache={}
        )
        product_key = f"product:{self.product.pk}"
        mapping = {
            "Nr": "member_no",
            "Start": "subscriptions:Vertragsbeginn",
            "Ende": "subscriptions:Vertragsende",
            "Käse": product_key,
        }
        DataImportMappingService.apply_rows(
            ["subscriptions"],
            fields,
            mapping,
            [
                {
                    "Nr": "101",
                    "Start": self.period.start_date.isoformat(),
                    "Ende": self.period.end_date.isoformat(),
                    "Käse": "2",
                }
            ],
            [0],
            False,
        )
        self.assertEqual(
            2,
            Subscription.objects.get(member=self.member, product=self.product).quantity,
        )

    def test_applyRows_overlappingExistingSubscription_updatesQuantity(self):
        existing = Subscription.objects.create(
            member=self.member,
            product=self.product,
            period=self.period,
            quantity=1,
            start_date=self.period.start_date,
            end_date=self.period.end_date,
            mandate_ref=MandateReferenceFactory(member=self.member),
            notice_period_duration=3,
            notice_period_unit="months",
        )
        fields = DataImportMappingService.build_semantic_fields(
            ["subscriptions"], cache={}
        )
        mapping = {
            "Nr": "member_no",
            "Start": "subscriptions:Vertragsbeginn",
            "Ende": "subscriptions:Vertragsende",
            "Käse": f"product:{self.product.pk}",
        }
        DataImportMappingService.apply_rows(
            ["subscriptions"],
            fields,
            mapping,
            [
                {
                    "Nr": "101",
                    "Start": self.period.start_date.isoformat(),
                    "Ende": self.period.end_date.isoformat(),
                    "Käse": "3",
                }
            ],
            [0],
            True,
        )
        existing.refresh_from_db()
        self.assertEqual(3, existing.quantity)
        self.assertEqual(
            1,
            Subscription.objects.filter(
                member=self.member, product=self.product
            ).count(),
        )

    def test_evaluate_overlappingSubscriptionWithUpdate_reportsQuantityChange(self):
        Subscription.objects.create(
            member=self.member,
            product=self.product,
            period=self.period,
            quantity=1,
            start_date=self.period.start_date,
            end_date=self.period.end_date,
            mandate_ref=MandateReferenceFactory(member=self.member),
            notice_period_duration=3,
            notice_period_unit="months",
        )
        fields = DataImportMappingService.build_semantic_fields(
            ["subscriptions"], cache={}
        )
        mapping = {
            "Nr": "member_no",
            "Start": "subscriptions:Vertragsbeginn",
            "Ende": "subscriptions:Vertragsende",
            "Käse": f"product:{self.product.pk}",
        }

        outcome = DataImportMappingService.evaluate(
            ["subscriptions"],
            fields,
            mapping,
            list(mapping),
            [
                {
                    "Nr": "101",
                    "Start": self.period.start_date.isoformat(),
                    "Ende": self.period.end_date.isoformat(),
                    "Käse": "3",
                }
            ],
            True,
        )[0]

        self.assertEqual("changed", outcome.status)
        self.assertIn("Käse: Menge 1 → 3", outcome.messages)

    def test_evaluateAndApplyRows_pz_assignsStableNumberAndEnablesTrial(self):
        fields = DataImportMappingService.build_semantic_fields(
            ["members", "subscriptions"], cache={}
        )
        mapping = {
            "Nr": "member_no",
            "Vorname": "members:Vorname",
            "Nachname": "members:Nachname",
            "Mail": "email",
            "Consent": "members:consent_sepa",
            "Start": "subscriptions:Vertragsbeginn",
            "Ende": "subscriptions:Vertragsende",
            "Käse": f"product:{self.product.pk}",
        }
        row = {
            "Nr": "PZ",
            "Vorname": "Probe",
            "Nachname": "Person",
            "Mail": "probe@example.org",
            "Consent": "01.03.2023",
            "Start": self.period.start_date.isoformat(),
            "Ende": self.period.end_date.isoformat(),
            "Käse": "1",
        }
        assigned = DataImportMappingService.assigned_member_numbers([row], mapping, {})
        outcome = DataImportMappingService.evaluate(
            ["members", "subscriptions"],
            fields,
            mapping,
            list(row),
            [row],
            False,
            assigned_member_numbers=assigned,
        )[0]
        shown = assigned[0]
        DataImportMappingService.apply_rows(
            ["members", "subscriptions"],
            fields,
            mapping,
            [row],
            [0],
            False,
            assigned_member_numbers=assigned,
        )
        member = Member.objects.get(member_no=shown)
        self.assertTrue(outcome.valid)
        self.assertTrue(
            Subscription.objects.get(member=member, product=self.product).trial_disabled
            is False
        )
        self.assertIn(str(shown), " ".join(outcome.messages))

    def test_applyRows_normalRow_disablesTrial(self):
        fields = DataImportMappingService.build_semantic_fields(
            ["members", "subscriptions"], cache={}
        )
        mapping = {
            "Nr": "member_no",
            "Vorname": "members:Vorname",
            "Nachname": "members:Nachname",
            "Mail": "email",
            "Consent": "members:consent_sepa",
            "Start": "subscriptions:Vertragsbeginn",
            "Ende": "subscriptions:Vertragsende",
            "Käse": f"product:{self.product.pk}",
        }
        row = {
            "Nr": "102",
            "Vorname": "Normal",
            "Nachname": "Person",
            "Mail": "normal@example.org",
            "Consent": "01.03.2023",
            "Start": self.period.start_date.isoformat(),
            "Ende": self.period.end_date.isoformat(),
            "Käse": "1",
        }
        DataImportMappingService.apply_rows(
            ["members", "subscriptions"], fields, mapping, [row], [0], False
        )
        member = Member.objects.get(member_no=102)
        self.assertTrue(
            Subscription.objects.get(member=member, product=self.product).trial_disabled
        )
