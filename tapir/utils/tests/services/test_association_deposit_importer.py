import datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.management import call_command

from tapir.associations.models import AssociationDepositTransaction
from tapir.associations.services.association_deposit_annotator import (
    AssociationDepositAnnotator,
)
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.utils.config import MEMBER_IMPORT_STATUS_SKIPPED
from tapir.utils.services.association_deposit_importer import AssociationDepositImporter
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositImporter(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self.membership = AssociationMembershipFactory.create(
            start_date=datetime.date(2025, 1, 1)
        )
        self.row = {
            "Nr": str(self.membership.member.member_no),
            "Einlage Erhalten": "150,00",
            "Einlage Offen": "50,00",
        }

    def test_importDeposit_receivedAndOutstanding_importsWithoutDebit(self):
        AssociationDepositImporter.import_deposit(self.row, {})
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_deposit(self.row, {}),
        )
        totals = AssociationDepositAnnotator.annotate_members(
            Member.objects.filter(pk=self.membership.member_id)
        ).get()
        self.assertEqual(200, totals.deposit_agreed)
        self.assertEqual(150, totals.deposit_exported)
        self.assertFalse(Payment.objects.exists())

    def test_importDeposit_replayAfterIncrease_preservesHistoricalBalance(self):
        AssociationDepositImporter.import_deposit(self.row, {})
        AssociationDepositPaymentCreator.create_deposit_and_payment(
            member=self.membership.member,
            amount=Decimal("50"),
            start_date=datetime.date(2026, 11, 5),
            actor=self.membership.member,
            cache={},
        )
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_deposit(self.row, {}),
        )
        self.assertEqual(3, AssociationDepositTransaction.objects.count())
        self.assertEqual(1, Payment.objects.count())

    def test_importDeposit_changedReplay_rejectsWithoutChangingBalances(self):
        AssociationDepositImporter.import_deposit(self.row, {})
        with self.assertRaisesMessage(ValidationError, "abweichende Einlagenbuchungen"):
            AssociationDepositImporter.import_deposit(
                {**self.row, "Einlage Offen": "60"}, {}
            )
        self.assertEqual(2, AssociationDepositTransaction.objects.count())

    def test_importDeposit_individualAgreement_createsRequestWithoutTransaction(self):
        row = {"Nr": self.row["Nr"], "Einlage Status": "offen"}
        AssociationDepositImporter.import_deposit(row, {})
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_deposit(row, {}),
        )
        self.membership.refresh_from_db()
        self.assertIsNotNone(self.membership.deposit_agreement_requested_at)
        self.assertFalse(AssociationDepositTransaction.objects.exists())
        self.assertFalse(Payment.objects.exists())

    def test_importDeposit_prefixedMemberNumber_usesExistingParser(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "GKK")
        AssociationDepositImporter.import_deposit(
            {**self.row, "Nr": f"GKK{self.row['Nr']}"}, {}
        )
        self.assertEqual(
            2,
            AssociationDepositTransaction.objects.filter(
                member=self.membership.member
            ).count(),
        )

    def test_importDeposit_unknownColumns_listsNames(self):
        with self.assertRaisesMessage(ValidationError, "Andere Spalte, Unbekannt"):
            AssociationDepositImporter.import_deposit(
                {**self.row, "Unbekannt": "x", "Andere Spalte": "y"}, {}
            )

    def test_importDeposit_emptyRow_isIgnored(self):
        self.assertIsNone(
            AssociationDepositImporter.import_deposit(
                {"Nr": "", "Einlage Erhalten": " "}, {}
            )
        )

    def test_importDeposit_dryRun_rollsBackTransactionsAndLogs(self):
        with TemporaryDirectory() as directory:
            path = Path(directory, "deposits.csv")
            path.write_text(f"Nr;Einlage Erhalten\n{self.row['Nr']};200,00\n;\n")
            output = StringIO()
            call_command(
                "import-data",
                "--type",
                "deposits",
                "--file",
                str(path),
                "--dry-run",
                stdout=output,
            )
        self.assertFalse(AssociationDepositTransaction.objects.exists())
        self.assertIn("Created: 1, Updated: 0, Skipped: 0", output.getvalue())
