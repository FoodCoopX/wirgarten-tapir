import datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationDeposit
from tapir.associations.services.association_deposit_importer import (
    AssociationDepositImporter,
)
from tapir.associations.services.association_deposit_departure_export import (
    AssociationDepositDepartureExport,
)
from tapir.associations.services.association_deposit_member_service import (
    AssociationDepositMemberService,
)
from tapir.associations.services.association_deposit_overview_provider import (
    AssociationDepositOverviewProvider,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.associations.tests.factories import (
    AssociationMembershipFactory,
    AssociationMembershipTypeFactory,
)
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.models import MandateReference, Member, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositImporter(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_importDeposit_dryRunAndRetry_preserveOneBalanceAndNoDebit(self):
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        member = MemberFactory(sepa_consent=None)
        membership = AssociationMembershipFactory(
            member=member, start_date=datetime.date(2025, 1, 1)
        )
        with TemporaryDirectory() as directory:
            path = Path(directory, "deposits.csv")
            path.write_text(f"Nr;Einlage Erhalten\n{member.member_no};200,00\n")
            call_command(
                "import-data",
                "--type",
                "deposits",
                "--file",
                str(path),
                "--dry-run",
                stdout=StringIO(),
            )
            self.assertFalse(AssociationDeposit.objects.exists())
            for _ in range(2):
                call_command(
                    "import-data",
                    "--type",
                    "deposits",
                    "--file",
                    str(path),
                    stdout=StringIO(),
                )
        self.assertEqual(
            Decimal("200"),
            AssociationDeposit.objects.get(membership=membership).opening_balance,
        )
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(MandateReference.objects.exists())

    def test_importDeposit_outstandingAndIndividualRequest_createNoPayment(self):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        membership = AssociationMembershipFactory(start_date=datetime.date(2025, 1, 1))
        requested = AssociationMembershipFactory(start_date=datetime.date(2025, 1, 1))
        rows = [
            {
                "Nr": str(membership.member.member_no),
                "Einlage Erhalten": "150,00",
                "Einlage Offen": "50,00",
            },
            {"Nr": str(requested.member.member_no), "Einlage Status": "offen"},
        ]
        for row in rows:
            AssociationDepositImporter.import_deposit(row, {})
            AssociationDepositImporter.import_deposit(row, {})
        with self.assertRaises(ValidationError):
            AssociationDepositImporter.import_deposit(
                {**rows[0], "Einlage Offen": "60"}, {}
            )
        overview = AssociationDepositOverviewProvider.annotate_members(
            Member.objects.all(), {}
        )
        balance = overview.get(pk=membership.member_id)
        self.assertEqual(Decimal("200"), balance.deposit_agreed)
        self.assertEqual(Decimal("150"), balance.deposit_exported)
        self.assertEqual(Decimal("50"), balance.deposit_imported_outstanding)
        self.assertTrue(
            overview.get(pk=requested.member_id).deposit_agreement_requested
        )
        self.assertEqual(2, AssociationDeposit.objects.count())
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(MandateReference.objects.exists())

    def test_importDeposit_rejoinedMember_rejectsAmbiguousReplay(self):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        former = AssociationMembershipFactory(
            start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2024, 12, 31)
        )
        row = {"Nr": str(former.member.member_no), "Einlage Erhalten": "200"}
        AssociationDepositImporter.import_deposit(row, {})
        new = AssociationMembershipFactory(
            member=former.member, start_date=datetime.date(2025, 3, 1)
        )
        with self.assertRaises(ValidationError):
            AssociationDepositImporter.import_deposit(row, {})
        self.assertTrue(former.deposits.exists())
        self.assertFalse(new.deposits.exists())

    def test_importDeposit_scheduledTypeChange_preservesBalanceAndDoesNotReportDeparture(
        self,
    ):
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        current = AssociationMembershipFactory(start_date=datetime.date(2026, 1, 1))
        member = current.member
        next_membership = AssociationMembershipChangeHandler.start_membership(
            member,
            AssociationMembershipTypeFactory(),
            datetime.date(2026, 12, 1),
            member,
            {},
        )
        row = {"Nr": str(member.member_no), "Einlage Erhalten": "200"}
        AssociationDepositImporter.import_deposit(row, {})
        self.assertEqual(
            next_membership.pk, AssociationDeposit.objects.get().membership_id
        )
        mock_timezone(self, datetime.datetime(2027, 1, 5, 12))
        AssociationDepositImporter.import_deposit(row, {})
        self.assertEqual(1, AssociationDeposit.objects.count())
        self.assertEqual(
            Decimal("200"),
            AssociationDepositMemberService.get_details(member, {})["amount"],
        )
        self.assertFalse(
            AssociationDepositDepartureExport.get_memberships(
                datetime.datetime(2027, 1, 5, 12)
            ).exists()
        )
        self.assertFalse(Payment.objects.exists())
