import io
import json
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status

from tapir.utils.services.data_import_mapping_service import DataImportMappingService
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


def excel_file(header, *rows):
    workbook = Workbook()
    workbook.active.append(header)
    for row in rows:
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile("Mitglieder.xlsx", buffer.getvalue())


def members_excel(header=None, row=None):
    return excel_file(
        header or ["Nr", "Vorname", "Nachname", "Mailadresse", "consent_sepa"],
        row or [101, "Erika", "Musterfrau", "erika@example.org", "01.03.2024"],
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

    def upload(self, file=None, import_types=None):
        response = self.client.post(
            reverse("utils:data_import_upload"),
            {
                "file": file or members_excel(),
                "import_types": import_types or ["members"],
            },
            format="multipart",
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        return response, response.data["token"]

    def mapping(self, token, values=None, defaults=None):
        values = values or [
            "member_no",
            "members:Vorname",
            "members:Nachname",
            "email",
            "members:consent_sepa",
        ]
        return self.client.post(
            reverse("utils:data_import_mapping"),
            json.dumps(
                {
                    "token": token,
                    "mapping": [
                        {"column_index": index, "key": key}
                        for index, key in enumerate(values)
                    ],
                    "defaults": [
                        {"key": key, "value": value}
                        for key, value in (defaults or {}).items()
                    ],
                }
            ),
            content_type="application/json",
        )

    def test_post_normalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        response = self.client.get(reverse("utils:data_import_types"))
        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_upload_returnsDistinctValuesAndExistingPickupLocations(self):
        location = PickupLocationFactory(name="Hof Nord")
        response, _ = self.upload(
            file=members_excel(
                ["Nr", "Vorname", "Nachname", "Mailadresse", "consent_sepa", "Depot"],
                [
                    101,
                    "Erika",
                    "Musterfrau",
                    "erika@example.org",
                    "01.03.2024",
                    "Hof Nord",
                ],
            )
        )
        self.assertEqual(
            {"id": str(location.id), "name": "Hof Nord"},
            next(
                item
                for item in response.data["pickup_locations"]
                if item["id"] == str(location.id)
            ),
        )
        depot = next(
            item
            for item in response.data["distinct_values"]
            if item["header"] == "Depot"
        )
        self.assertEqual([{"value": "Hof Nord", "count": 1}], depot["values"])

    def test_post_upload_returnsAutoMapping(self):
        response, _ = self.upload()
        self.assertEqual("member_no", response.data["columns"][0]["selected_key"])
        self.assertEqual("email", response.data["columns"][3]["selected_key"])

    def test_post_uploadWithCommaSeparatedImportTypes_acceptsAllTypes(self):
        # This is how the generated TS client sends arrays in multipart forms.
        response, _ = self.upload(import_types="members,shares")

        self.assertEqual(
            ["Mitglieder", "Genossenschaftsanteile"],
            response.data["selected_type_names"],
        )

    def test_post_mapping_missingRequired_returnsErrors(self):
        _, token = self.upload()
        response = self.mapping(
            token,
            [
                "member_no",
                "members:Vorname",
                "members:Nachname",
                "",
                "members:consent_sepa",
            ],
        )
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertTrue(
            any("Mailadresse" in error for error in response.data["mapping_errors"])
        )

    def test_post_mapping_defaultForPersonalField_isIgnored(self):
        _, token = self.upload()
        response = self.mapping(
            token,
            [
                "member_no",
                "members:Vorname",
                "members:Nachname",
                "",
                "members:consent_sepa",
            ],
            defaults={"email": "alle@example.org"},
        )
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertTrue(
            any("Mailadresse" in error for error in response.data["mapping_errors"])
        )

    def test_post_uploadMappingApply_createsMember(self):
        _, token = self.upload()
        response = self.mapping(token)
        self.assertEqual(1, response.data["valid_count"])
        response = self.client.post(
            reverse("utils:data_import_apply"),
            json.dumps({"token": token, "row_indices": [0]}),
            content_type="application/json",
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertTrue(Member.objects.filter(member_no=101).exists())

    def test_post_applyNonValidatedIndex_returnsErrorAndCreatesNothing(self):
        _, token = self.upload()
        self.mapping(token)
        response = self.client.post(
            reverse("utils:data_import_apply"),
            json.dumps({"token": token, "row_indices": [5]}),
            content_type="application/json",
        )
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertFalse(Member.objects.filter(member_no=101).exists())

    def edit_cell(self, token, header, value, row_index=0):
        return self.client.post(
            reverse("utils:data_import_cell"),
            json.dumps(
                {
                    "token": token,
                    "row_index": row_index,
                    "header": header,
                    "value": value,
                }
            ),
            content_type="application/json",
        )

    def test_post_cellFixesInvalidDate_rowBecomesValidAndIsApplied(self):
        _, token = self.upload(
            file=members_excel(
                row=[101, "Erika", "Musterfrau", "erika@example.org", "kein Datum"]
            )
        )
        self.assertEqual(0, self.mapping(token).data["valid_count"])

        response = self.edit_cell(token, "consent_sepa", "01.03.2024")

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, response.data["valid_count"])
        cell = response.data["rows"][0]["cells"][4]
        self.assertTrue(cell["edited"])
        self.assertEqual("kein Datum", cell["original_value"])
        self.client.post(
            reverse("utils:data_import_apply"),
            json.dumps({"token": token, "row_indices": [0]}),
            content_type="application/json",
        )
        self.assertTrue(Member.objects.filter(member_no=101).exists())

    def test_post_cell_overrideSurvivesResubmittedMapping(self):
        _, token = self.upload()
        self.mapping(token)
        self.edit_cell(token, "Nachname", "Neumann")

        response = self.mapping(token)

        self.assertEqual("Neumann", response.data["rows"][0]["cells"][2]["value"])

    def test_post_cellValueEqualToOriginal_removesOverride(self):
        _, token = self.upload()
        self.mapping(token)
        self.edit_cell(token, "Nachname", "Neumann")

        response = self.edit_cell(token, "Nachname", "Musterfrau")

        cell = response.data["rows"][0]["cells"][2]
        self.assertEqual("Musterfrau", cell["value"])
        self.assertFalse(cell.get("edited", False))

    def test_post_cellOfExistingMemberWithoutUpdate_returns400(self):
        MemberFactory.create(member_no=101)
        _, token = self.upload()
        self.mapping(token)

        response = self.edit_cell(token, "Nachname", "Neumann")

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_post_unknownToken_returnsExpiredError(self):
        response = self.client.post(
            reverse("utils:data_import_mapping"),
            json.dumps({"token": "unknown", "mapping": []}),
            content_type="application/json",
        )
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            "Die hochgeladene Datei ist abgelaufen, bitte noch einmal hochladen.",
            response.data["detail"],
        )

    def test_get_template_returnsExcelFile(self):
        response = self.client.get(
            reverse("utils:data_import_template", args=["members"])
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIn("Vorlage Mitglieder.xlsx", response["Content-Disposition"])

    def test_post_mapping_missingRequiredField_listsFieldInResponse(self):
        _, token = self.upload()
        response = self.mapping(
            token,
            [
                "member_no",
                "members:Vorname",
                "members:Nachname",
                "",
                "members:consent_sepa",
            ],
        )
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertTrue(
            any("Mailadresse" in error for error in response.data["mapping_errors"])
        )
