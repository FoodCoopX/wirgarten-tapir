import datetime

from tapir.utils.config import MEMBER_IMPORT_STATUS_CREATED
from tapir.utils.services.share_importer import ShareImporter
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestShareImporter(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def build_row(
        self,
        member_no,
        transaction_type_key,
        date_string,
        transfer_partner_member_no="",
        number_of_shares="2",
    ):
        return {
            "Mitgliedsnummer": str(member_no),
            "Bewegungsart (Z,Ü,K)": transaction_type_key,
            "Datum": date_string,
            "Anzahl Anteile": number_of_shares,
            "Wert Anteile": "100",
            "Übertragungspartner": str(transfer_partner_member_no),
            "Wirkung Kündigung": date_string,
        }

    def test_importSharesSingleMember_purchaseValidInThePast_marksMembershipMailAsAlreadySent(
        self,
    ):
        # Members imported from an external system with shares already valid
        # in the past were already members before Tapir existed, so they
        # must not receive the "welcome, your membership just started" mail.
        mock_timezone(test=self, now=datetime.datetime(year=2021, month=5, day=1))
        member = MemberFactory.create(
            member_no=1, has_received_membership_started_mail=False
        )

        row = self.build_row(
            member_no=member.member_no,
            transaction_type_key="Z",
            date_string="2020-01-01",
        )

        status = ShareImporter.import_shares_single_member(
            row=row, update_existing=False
        )

        self.assertEqual(MEMBER_IMPORT_STATUS_CREATED, status)
        member.refresh_from_db()
        self.assertTrue(member.has_received_membership_started_mail)

    def test_importSharesSingleMember_transferInValidInThePast_marksMembershipMailAsAlreadySent(
        self,
    ):
        mock_timezone(test=self, now=datetime.datetime(year=2021, month=5, day=1))
        transfer_partner = MemberFactory.create(member_no=2)
        member = MemberFactory.create(
            member_no=1, has_received_membership_started_mail=False
        )

        row = self.build_row(
            member_no=member.member_no,
            transaction_type_key="Ü",
            date_string="2020-01-01",
            transfer_partner_member_no=transfer_partner.member_no,
        )

        status = ShareImporter.import_shares_single_member(
            row=row, update_existing=False
        )

        self.assertEqual(MEMBER_IMPORT_STATUS_CREATED, status)
        member.refresh_from_db()
        self.assertTrue(member.has_received_membership_started_mail)

    def test_importSharesSingleMember_cancellationInThePast_doesNotMarkMembershipMailAsSent(
        self,
    ):
        # A cancellation isn't a "membership started" event, so it must not
        # be treated the same as a purchase or transfer-in, regardless of
        # its date.
        mock_timezone(test=self, now=datetime.datetime(year=2021, month=5, day=1))
        member = MemberFactory.create(
            member_no=1, has_received_membership_started_mail=False
        )

        row = self.build_row(
            member_no=member.member_no,
            transaction_type_key="K",
            date_string="2020-01-01",
            number_of_shares="-2",
        )

        status = ShareImporter.import_shares_single_member(
            row=row, update_existing=False
        )

        self.assertEqual(MEMBER_IMPORT_STATUS_CREATED, status)
        member.refresh_from_db()
        self.assertFalse(member.has_received_membership_started_mail)
