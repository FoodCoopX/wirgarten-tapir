import json

from django.core.mail import EmailMessage
from django.urls import reverse
from rest_framework import status

from tapir.log.models import EmailLogEntry
from tapir.core.services.member_data_disclosure_service import DATA_SOURCES
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberDataDisclosureApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def get(self, name: str, member_id: str, **params):
        url = reverse(f"core:{name}")
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return self.client.get(f"{url}?member_id={member_id}&{query}")

    def test_get_otherMember_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.get("member_data_disclosure", member.id)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_ownData_returnsAllSectionsWithPersonalData(self):
        member = MemberFactory.create(
            first_name="Erika", last_name="Muster", is_superuser=False
        )
        self.client.force_login(member)

        response = self.get("member_data_disclosure", member.id)

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            [source.key for source in DATA_SOURCES],
            [section["key"] for section in data["sections"]],
        )
        personal_data = next(s for s in data["sections"] if s["key"] == "personal_data")
        values = {
            field["name"]: field["value"] for field in personal_data["records"][0]
        }
        self.assertEqual("Erika", values["first_name"])
        self.assertEqual("Muster", values["last_name"])

    def test_get_otherMembersDataNotIncluded(self):
        member = MemberFactory.create(is_superuser=False)
        other = MemberFactory.create(first_name="Fremdername")
        self.client.force_login(member)

        response = self.get("member_data_disclosure", member.id)

        self.assertNotIn("Fremdername", response.content.decode())
        self.assertNotIn(other.email, response.content.decode())

    def test_get_adminReadsMemberData_returns200(self):
        member = MemberFactory.create()
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.get("member_data_disclosure", member.id)

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_download_json_returnsRecordsAsObjects(self):
        member = MemberFactory.create(first_name="Erika", is_superuser=False)
        self.client.force_login(member)

        response = self.get(
            "member_data_disclosure_download", member.id, file_type="json"
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertIn("attachment", response["Content-Disposition"])
        data = json.loads(response.content)
        personal_data = next(s for s in data["sections"] if s["key"] == "personal_data")
        self.assertEqual("Erika", personal_data["records"][0]["first_name"])

    def test_download_pdf_returnsPdf(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.get(
            "member_data_disclosure_download", member.id, file_type="pdf"
        )

        # assertStatusCode decodes the body as text, which a PDF is not
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual("application/pdf", response["Content-Type"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_download_otherMember_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.get(
            "member_data_disclosure_download", member.id, file_type="json"
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_memberHasMailsAndLogEntries_returnsOnlyOverview(self):
        member = MemberFactory.create(is_superuser=False)
        for _ in range(2):
            EmailLogEntry().populate(
                email_message=EmailMessage(subject="Geheimer Betreff", body="Inhalt"),
                actor=None,
                user=member,
            ).save()
        self.client.force_login(member)

        response = self.get("member_data_disclosure", member.id)

        data = response.json()
        self.assertEqual(2, data["mail_overview"]["count"])
        self.assertEqual(
            [("email log entry", 2)],
            [(entry["type"].lower(), entry["count"]) for entry in data["log_overview"]],
        )
        self.assertNotIn("Geheimer Betreff", response.content.decode())
        self.assertNotIn("Inhalt", response.content.decode())
