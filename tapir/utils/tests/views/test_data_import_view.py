import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status

from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


def members_excel() -> SimpleUploadedFile:
    workbook = Workbook()
    workbook.active.append(["Nr", "Vorname", "Nachname", "Mailadresse", "consent_sepa"])
    workbook.active.append(
        [101, "Erika", "Musterfrau", "erika@example.org", "01.03.2024"]
    )
    buffer = io.BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile("Mitglieder.xlsx", buffer.getvalue())


class TestDataImportView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(reverse("utils:data_import"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_loggedInAsAdmin_returns200(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(reverse("utils:data_import"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_template_returnsExcelFile(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(
            reverse("utils:data_import_template", args=["members"])
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIn("Vorlage Mitglieder.xlsx", response["Content-Disposition"])

    def test_uploadThenApply_importsTheMemberOnlyAfterApply(self):
        admin = MemberFactory.create(is_superuser=True, member_no=1)
        self.client.force_login(admin)

        response = self.client.post(
            reverse("utils:data_import"),
            {"import_type": "members", "file": members_excel()},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertContains(response, "1 werden angelegt")
        self.assertFalse(Member.objects.filter(member_no=101).exists())

        response = self.client.post(
            reverse("utils:data_import_apply"),
            {"token": response.context["token"]},
        )

        self.assertRedirects(response, reverse("utils:data_import"))
        member = Member.objects.get(member_no=101)
        self.assertEqual("erika@example.org", member.email)
