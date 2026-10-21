import io
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status

from tapir.utils.services.data_import_mapping_service import DataImportMappingService
from tapir.wirgarten.models import CoopShareTransaction, Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


def excel_file(filename: str, header: list, *data_rows: list) -> SimpleUploadedFile:
    workbook = Workbook()
    workbook.active.append(header)
    for row in data_rows:
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(filename, buffer.getvalue())


def members_excel(header=None) -> SimpleUploadedFile:
    header = header or ["Nr", "Vorname", "Nachname", "Mailadresse", "consent_sepa"]
    return excel_file(
        "Mitglieder.xlsx",
        header,
        [101, "Erika", "Musterfrau", "erika@example.org", "01.03.2024"],
    )


def members_and_shares_excel() -> SimpleUploadedFile:
    header = [
        "Mitgliedsnummer",
        "Vorname",
        "Nachname",
        "Mailadresse",
        "consent_sepa",
        "Bewegungsart (Z,Ü,K)",
        "Datum",
        "Anzahl Anteile",
    ]
    return excel_file(
        "Mitglieder_und_Anteile.xlsx",
        header,
        [
            101,
            "Erika",
            "Musterfrau",
            "erika@example.org",
            "01.03.2024",
            "Z",
            "01.03.2024",
            2,
        ],
        [
            102,
            "Hans",
            "Mustermann",
            "hans@example.org",
            "01.03.2024",
            "Z",
            "01.03.2024",
            2,
        ],
    )


class TestDataImportView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self.admin = MemberFactory.create(is_superuser=True, member_no=1)
        self.client.force_login(self.admin)

    def tearDown(self):
        cache.clear()

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(reverse("utils:data_import"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_loggedInAsAdmin_returns200(self):
        response = self.client.get(reverse("utils:data_import"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_template_returnsExcelFile(self):
        response = self.client.get(
            reverse("utils:data_import_template", args=["members"])
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIn("Vorlage Mitglieder.xlsx", response["Content-Disposition"])

    def test_upload_noTypeSelected_formIsInvalid(self):
        response = self.client.post(
            reverse("utils:data_import"),
            {"file": members_excel()},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("upload", response.context["stage"])
        self.assertFormError(
            response.context["form"],
            "import_types",
            "Mindestens ein Typ muss ausgewählt werden.",
        )

    def test_upload_singleType_autoMapsExactHeadersAndShowsMappingStage(self):
        response = self.client.post(
            reverse("utils:data_import"),
            {"import_types": ["members"], "file": members_excel()},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("mapping", response.context["stage"])
        columns_by_header = {
            column["header"]: column for column in response.context["columns"]
        }
        self.assertEqual("member_no", columns_by_header["Nr"]["selected_key"])
        self.assertEqual(
            "members:Vorname", columns_by_header["Vorname"]["selected_key"]
        )
        self.assertEqual(
            "members:Mailadresse", columns_by_header["Mailadresse"]["selected_key"]
        )

    def test_upload_synonymHeaders_autoMapToleratesVariants(self):
        response = self.client.post(
            reverse("utils:data_import"),
            {
                "import_types": ["members"],
                "file": members_excel(
                    header=[
                        "Mitgliedsnummer",
                        "First Name",
                        "Last Name",
                        "E-Mail",
                        "consent_sepa",
                    ]
                ),
            },
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        columns_by_header = {
            column["header"]: column for column in response.context["columns"]
        }
        self.assertEqual(
            "member_no", columns_by_header["Mitgliedsnummer"]["selected_key"]
        )
        self.assertEqual(
            "members:Vorname", columns_by_header["First Name"]["selected_key"]
        )
        self.assertEqual(
            "members:Nachname", columns_by_header["Last Name"]["selected_key"]
        )
        self.assertEqual(
            "members:Mailadresse", columns_by_header["E-Mail"]["selected_key"]
        )

    def _upload(self, import_types, upload):
        response = self.client.post(
            reverse("utils:data_import"),
            {"import_types": import_types, "file": upload},
        )
        return response.context["token"]

    def test_mapping_requiredFieldUnmapped_staysOnMappingStageWithServerSideError(self):
        token = self._upload(["members"], members_excel())

        post_data = {
            "token": token,
            "col_0": "member_no",
            "col_1": "members:Vorname",
            "col_2": "members:Nachname",
            # col_3 (Mailadresse, required) intentionally left unmapped/tampered
            "col_3": "do_not_import",
            "col_4": "members:consent_sepa",
        }
        response = self.client.post(reverse("utils:data_import_mapping"), post_data)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("mapping", response.context["stage"])
        self.assertTrue(
            any("Mailadresse" in error for error in response.context["mapping_errors"])
        )

    def test_mapping_duplicateTargetAssignment_isRejectedServerSide(self):
        token = self._upload(["members"], members_excel())

        post_data = {
            "token": token,
            "col_0": "member_no",
            "col_1": "members:Vorname",
            "col_2": "members:Vorname",  # duplicate target
            "col_3": "members:Mailadresse",
            "col_4": "members:consent_sepa",
        }
        response = self.client.post(reverse("utils:data_import_mapping"), post_data)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("mapping", response.context["stage"])
        self.assertTrue(
            any(
                "nur einer Spalte" in error
                for error in response.context["mapping_errors"]
            )
        )

    def test_mapping_unknownPostedTarget_fallsBackToDoNotImport(self):
        """Posting a semantic key that does not belong to the selected types (tampered client)
        must not be accepted; it is silently treated as 'do not import' and so still triggers
        the usual required-field check."""
        token = self._upload(["members"], members_excel())

        post_data = {
            "token": token,
            "col_0": "member_no",
            "col_1": "members:Vorname",
            "col_2": "members:Nachname",
            "col_3": "subscriptions:product",  # not a valid target for "members" only
            "col_4": "members:consent_sepa",
        }
        response = self.client.post(reverse("utils:data_import_mapping"), post_data)

        self.assertEqual("mapping", response.context["stage"])
        self.assertTrue(
            any("Mailadresse" in error for error in response.context["mapping_errors"])
        )

    def _map_default(self, token, mapping: dict):
        post_data = {"token": token}
        post_data.update(mapping)
        return self.client.post(reverse("utils:data_import_mapping"), post_data)

    def test_mapping_validCompleteMapping_advancesToReviewAndRowIsValid(self):
        token = self._upload(["members"], members_excel())

        response = self._map_default(
            token,
            {
                "col_0": "member_no",
                "col_1": "members:Vorname",
                "col_2": "members:Nachname",
                "col_3": "members:Mailadresse",
                "col_4": "members:consent_sepa",
            },
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("review", response.context["stage"])
        self.assertEqual(1, response.context["valid_count"])
        self.assertEqual(0, response.context["invalid_count"])
        self.assertFalse(Member.objects.filter(member_no=101).exists())

    def test_combinedTypes_sharedMemberNumberColumn_bothImportersSucceedInReview(self):
        token = self._upload(["members", "shares"], members_and_shares_excel())

        response = self._map_default(
            token,
            {
                "col_0": "member_no",
                "col_1": "members:Vorname",
                "col_2": "members:Nachname",
                "col_3": "members:Mailadresse",
                "col_4": "members:consent_sepa",
                "col_5": "shares:Bewegungsart (Z,Ü,K)",
                "col_6": "shares:Datum",
                "col_7": "shares:Anzahl Anteile",
            },
        )

        self.assertEqual("review", response.context["stage"])
        self.assertEqual(2, response.context["valid_count"])
        row = response.context["review_rows"][0]
        self.assertTrue(row["valid"])
        for cell in row["cells"]:
            self.assertNotEqual("invalid", cell["state"])

    def test_apply_appliesOnlySelectedValidRows(self):
        token = self._upload(["members"], members_excel())
        self._map_default(
            token,
            {
                "col_0": "member_no",
                "col_1": "members:Vorname",
                "col_2": "members:Nachname",
                "col_3": "members:Mailadresse",
                "col_4": "members:consent_sepa",
            },
        )

        response = self.client.post(
            reverse("utils:data_import_apply"), {"token": token, "rows": ["0"]}
        )

        self.assertRedirects(response, reverse("utils:data_import"))
        member = Member.objects.get(member_no=101)
        self.assertEqual("erika@example.org", member.email)

    def test_apply_postedRowNotInCachedValidSet_isRejectedAndNothingIsImported(self):
        token = self._upload(["members"], members_excel())
        self._map_default(
            token,
            {
                "col_0": "member_no",
                "col_1": "members:Vorname",
                "col_2": "members:Nachname",
                "col_3": "members:Mailadresse",
                "col_4": "members:consent_sepa",
            },
        )

        # Row index 5 was never validated/cached as valid -> must be rejected.
        response = self.client.post(
            reverse("utils:data_import_apply"), {"token": token, "rows": ["5"]}
        )

        self.assertRedirects(response, reverse("utils:data_import"))
        self.assertFalse(Member.objects.filter(member_no=101).exists())

    def test_apply_oneRowFailsAtApplyTime_rollsBackTheWholeSelectedBatch(self):
        token = self._upload(["members", "shares"], members_and_shares_excel())
        self._map_default(
            token,
            {
                "col_0": "member_no",
                "col_1": "members:Vorname",
                "col_2": "members:Nachname",
                "col_3": "members:Mailadresse",
                "col_4": "members:consent_sepa",
                "col_5": "shares:Bewegungsart (Z,Ü,K)",
                "col_6": "shares:Datum",
                "col_7": "shares:Anzahl Anteile",
            },
        )

        # Simulate an unexpected failure while applying the second of two otherwise-valid rows
        # (e.g. a race condition). The whole selected batch must be rolled back: nothing may be
        # committed, including the row that would have succeeded on its own.
        original_apply_row = DataImportMappingService.apply_row
        calls = {"count": 0}

        def failing_apply_row(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("Simulated unexpected failure")
            return original_apply_row(*args, **kwargs)

        with patch.object(
            DataImportMappingService, "apply_row", side_effect=failing_apply_row
        ):
            response = self.client.post(
                reverse("utils:data_import_apply"),
                {"token": token, "rows": ["0", "1"]},
            )

        self.assertRedirects(response, reverse("utils:data_import"))
        self.assertFalse(Member.objects.filter(member_no=101).exists())
        self.assertFalse(Member.objects.filter(member_no=102).exists())
        self.assertFalse(CoopShareTransaction.objects.exists())
