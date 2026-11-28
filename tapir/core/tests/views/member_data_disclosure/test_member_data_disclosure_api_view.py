from django.core.mail import EmailMessage
from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION, LEGAL_STATUS_COOPERATIVE
from tapir.core.services.member_data_disclosure_service import DATA_SOURCES
from tapir.log.models import EmailLogEntry
from tapir.wirgarten.models import (
    CoopShareTransaction,
    QuestionaireTrafficSourceOption,
    QuestionaireTrafficSourceResponse,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.member import transfer_coop_shares
from tapir.wirgarten.tests.factories import (
    MandateReferenceFactory,
    MemberFactory,
    MemberWithCoopSharesFactory,
    PaymentFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberDataDisclosureApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def get_data(self, member_id: str):
        url = reverse("core:member_data_disclosure")
        return self.client.get(f"{url}?member_id={member_id}")

    @staticmethod
    def set_legal_status(legal_status: str):
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=legal_status)

    @staticmethod
    def get_section(data: dict, key: str) -> dict | None:
        return next((s for s in data["sections"] if s["key"] == key), None)

    def test_get_otherMember_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.get_data(member.id)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_adminReadsMemberData_returns200(self):
        member = MemberFactory.create()
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.get_data(member.id)

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_ownData_returnsPersonalDataAndPdfUrl(self):
        member = MemberFactory.create(
            first_name="Erika", last_name="Muster", is_superuser=False
        )
        self.client.force_login(member)

        response = self.get_data(member.id)

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        personal_data = self.get_section(data, "personal_data")
        values = {
            field["name"]: field["value"] for field in personal_data["records"][0]
        }
        self.assertEqual("Erika", values["first_name"])
        self.assertEqual("Muster", values["last_name"])
        self.assertIn(reverse("core:member_data_disclosure_pdf"), data["pdf_url"])

    def test_get_sharesTransferredToOtherMember_otherMembersNameNotIncluded(self):
        self.set_legal_status(LEGAL_STATUS_COOPERATIVE)
        origin = MemberWithCoopSharesFactory.create(
            first_name="Abgebende", is_superuser=False
        )
        target = MemberFactory.create(first_name="Empfangende", last_name="Fremd")
        transfer_coop_shares(origin.id, target.id, 1, actor=origin)
        transfer_out = CoopShareTransaction.objects.get(
            member=origin,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.TRANSFER_OUT,
        )
        PaymentFactory.create(
            mandate_ref=MandateReferenceFactory.create(member=origin),
            coop_share_transaction=transfer_out,
        )
        self.client.force_login(origin)

        response = self.get_data(origin.id)

        content = response.content.decode()
        self.assertNotIn("Empfangende", content)
        self.assertNotIn("Fremd", content)
        self.assertNotIn(target.email, content)

    def test_get_memberReceivedShares_transferLogEntryCounted(self):
        origin = MemberWithCoopSharesFactory.create()
        target = MemberFactory.create(is_superuser=False)
        transfer_coop_shares(origin.id, target.id, 1, actor=origin)
        self.client.force_login(target)

        response = self.get_data(target.id)

        log_types = [entry["type"].lower() for entry in response.json()["log_overview"]]
        self.assertTrue(any("transfer" in log_type for log_type in log_types))
        self.assertNotIn(origin.first_name, response.content.decode())

    def test_get_organisationIsAssociation_coopSharesHidden(self):
        self.set_legal_status(LEGAL_STATUS_ASSOCIATION)
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        data = self.get_data(member.id).json()

        self.assertIsNone(self.get_section(data, "coop_shares"))
        self.assertIsNotNone(self.get_section(data, "association_memberships"))

    def test_get_organisationIsCooperative_associationMembershipsHidden(self):
        self.set_legal_status(LEGAL_STATUS_COOPERATIVE)
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        data = self.get_data(member.id).json()

        self.assertIsNotNone(self.get_section(data, "coop_shares"))
        self.assertIsNone(self.get_section(data, "association_memberships"))

    def test_get_trafficSourceAnswered_selectedSourcesShown(self):
        member = MemberFactory.create(is_superuser=False)
        response_object = QuestionaireTrafficSourceResponse.objects.create(
            member=member
        )
        response_object.sources.add(
            QuestionaireTrafficSourceOption.objects.create(name="Flyer"),
            QuestionaireTrafficSourceOption.objects.create(name="Freunde"),
        )
        self.client.force_login(member)

        data = self.get_data(member.id).json()

        section = self.get_section(data, "traffic_source")
        values = {field["name"]: field["value"] for field in section["records"][0]}
        self.assertEqual({"Flyer", "Freunde"}, set(values["sources"].split(", ")))

    def test_get_memberHasMailsAndLogEntries_returnsOnlyOverview(self):
        member = MemberFactory.create(is_superuser=False)
        for _ in range(2):
            EmailLogEntry().populate(
                email_message=EmailMessage(subject="Geheimer Betreff", body="Inhalt"),
                actor=None,
                user=member,
            ).save()
        self.client.force_login(member)

        response = self.get_data(member.id)

        data = response.json()
        self.assertEqual(2, data["mail_overview"]["count"])
        self.assertEqual(
            [("email log entry", 2)],
            [(entry["type"].lower(), entry["count"]) for entry in data["log_overview"]],
        )
        self.assertNotIn("Geheimer Betreff", response.content.decode())
        self.assertNotIn("Inhalt", response.content.decode())

    def test_get_cooperative_sectionsFollowDataSourceOrder(self):
        self.set_legal_status(LEGAL_STATUS_COOPERATIVE)
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        data = self.get_data(member.id).json()

        keys = [section["key"] for section in data["sections"]]
        expected = [source.key for source in DATA_SOURCES if source.key in keys]
        self.assertEqual(expected, keys)
        self.assertIn("personal_data", keys)
