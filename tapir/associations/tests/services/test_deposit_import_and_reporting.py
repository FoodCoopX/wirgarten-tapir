import datetime
import io
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError

from tapir.associations.models import AssociationDeposit
from tapir.associations.services.association_deposit_service import (
    AssociationDepositService,
)
from tapir.associations.services.deposit_configuration import DepositConfiguration
from tapir.associations.services.deposit_reporting import DepositReporting
from tapir.generic_exports.models import CsvExport
from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.services.csv_templates.template_association_deposit_refunds import (
    TemplateAssociationDepositRefunds,
)
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
)
from tapir.utils.services.association_deposit_importer import AssociationDepositImporter
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_today


class TestDepositImportAndReporting(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory()
        self.today = get_today({})
        self.row = {
            "Buchungs-ID": "legacy-001",
            "Mitgliedsnummer": str(self.member.member_no),
            "Betrag": "200,00",
            "Datum": str(self.today - datetime.timedelta(days=400)),
            "Austrittsdatum": str(self.today - datetime.timedelta(days=30)),
        }

    def instalment_row(self):
        overdue = self.today - datetime.timedelta(days=5)
        future = self.today + datetime.timedelta(days=60)
        return {
            **self.row,
            "Austrittsdatum": "",
            "Status": "vereinbart",
            "Betrag": "50,00",
            "Gesamtbetrag": "100,01",
            "Offene Raten": f"{overdue}:25,01|{future}:25,00",
            "Vereinbarung": "Reduzierung und Raten laut unterschriebener Vereinbarung A-42",
        }

    def hardship_row(self):
        return {
            **self.row,
            "Status": "haertefall",
            "Betrag": "0",
            "Datum": "",
            "Austrittsdatum": "",
            "Gesamtbetrag": "",
            "Offene Raten": "",
            "Vereinbarung": "",
        }

    def test_paid_balance_and_only_open_instalments_keep_exact_amounts_and_dates(self):
        row = self.instalment_row()
        self.assertEqual(
            MEMBER_IMPORT_STATUS_CREATED,
            AssociationDepositImporter.import_opening_balance(row, {}),
        )
        deposit = AssociationDeposit.objects.get()
        self.assertEqual(Decimal("100.01"), deposit.agreed_amount)
        self.assertTrue(deposit.exception_authorized)
        self.assertEqual(Decimal("50"), deposit.bookings.get().amount)
        expected = [
            (Decimal("25.01"), self.today - datetime.timedelta(days=5)),
            (Decimal("25"), self.today + datetime.timedelta(days=60)),
        ]
        self.assertEqual(
            expected,
            list(
                deposit.payments.order_by("due_date").values_list("amount", "due_date")
            ),
        )
        self.assertEqual(
            Decimal("50"), AssociationDepositService.balances(deposit, {})["balance"]
        )
        self.assertEqual(
            Decimal("50.01"), AssociationDepositService.balances(deposit, {})["pending"]
        )
        before = list(deposit.payments.order_by("pk").values())
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_opening_balance(row, {}),
        )
        self.assertEqual(before, list(deposit.payments.order_by("pk").values()))
        self.assertEqual(1, deposit.operations.count())
        self.assertEqual(1, deposit.bookings.count())
        self.assertFalse(
            deposit.payments.exclude(status=Payment.PaymentStatus.DUE).exists()
        )

    def test_imported_hardship_is_visible_without_debt_exemption_or_notification(self):
        with patch(
            "tapir.associations.services.deposit_mail_service.DepositMailService.notify_pending_agreement"
        ) as notify:
            with self.captureOnCommitCallbacks(execute=True):
                for status in [
                    MEMBER_IMPORT_STATUS_CREATED,
                    MEMBER_IMPORT_STATUS_SKIPPED,
                ]:
                    self.assertEqual(
                        status,
                        AssociationDepositImporter.import_opening_balance(
                            self.hardship_row(), {}
                        ),
                    )
            notify.assert_not_called()
        deposit = AssociationDeposit.objects.get()
        self.assertTrue(deposit.hardship_pending)
        self.assertIsNone(deposit.agreed_amount)
        self.assertFalse(deposit.exception_authorized)
        self.assertFalse(deposit.bookings.exists())
        self.assertFalse(deposit.payments.exists())
        self.assertEqual(
            1,
            DepositReporting.filter_members(
                Member.objects.all(), "pending", {}
            ).count(),
        )
        self.assertEqual(1, DepositReporting.dashboard({})["pending_cases"])
        self.assertEqual(
            0, AssociationDepositService.balances(deposit, {})["refundable"]
        )

    def test_imported_hardship_can_only_be_resolved_by_new_documented_agreement(self):
        row = self.hardship_row()
        AssociationDepositImporter.import_opening_balance(row, {})
        with self.assertRaisesMessage(ValidationError, "andere Angaben"):
            AssociationDepositImporter.import_opening_balance(self.instalment_row(), {})
        with self.assertRaisesMessage(ValidationError, "zweiter Anfangsbestand"):
            AssociationDepositImporter.import_opening_balance(
                {**self.instalment_row(), "Buchungs-ID": "second"}, {}
            )
        config = {**DepositConfiguration.get({}), "enabled": True}
        with patch.object(DepositConfiguration, "get", return_value=config):
            AssociationDepositService.apply(
                self.member,
                {
                    "action": "agreement",
                    "amount": "0",
                    "note": "Vollständiger Verzicht mit Mitglied vereinbart",
                },
                "waiver",
                self.member,
                {},
                True,
            )
        AssociationDepositImporter.import_opening_balance(row, {})
        deposit = AssociationDeposit.objects.get()
        self.assertFalse(deposit.hardship_pending)
        self.assertEqual(0, deposit.agreed_amount)
        self.assertTrue(deposit.exception_authorized)
        self.assertFalse(deposit.payments.exists())

    def test_conflicting_repetition_keeps_original_bookings_and_schedule(self):
        row = self.instalment_row()
        AssociationDepositImporter.import_opening_balance(row, {})
        before = list(Payment.objects.order_by("pk").values())
        for change in [
            {"Gesamtbetrag": "200"},
            {"Betrag": "25"},
            {"Offene Raten": f"{self.today}:50,01"},
            {"Vereinbarung": "Anderer Beleg"},
            {"Buchungs-ID": "another"},
        ]:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                AssociationDepositImporter.import_opening_balance({**row, **change}, {})
        self.assertEqual(before, list(Payment.objects.order_by("pk").values()))
        deposit = AssociationDeposit.objects.get()
        self.assertEqual(1, deposit.operations.count())
        self.assertEqual(1, deposit.bookings.count())

    def test_invalid_import_is_atomic(self):
        row = self.instalment_row()
        for change in [
            {"Gesamtbetrag": "100.02"},
            {"Gesamtbetrag": ""},
            {"Vereinbarung": ""},
            {"Datum": str(self.today + datetime.timedelta(days=1))},
            {"Offene Raten": "2030-02-30:50,01"},
            {"Offene Raten": "2030-01-01:0|2030-02-01:50,01"},
            {"Offene Raten": "2030-01-01:25|2030-01-01:25,01"},
            {"Offene Raten": "2030-02-01:25|2030-01-01:25,01"},
            {"Offene Raten": "2030-01-01:50,001"},
            {"Offene Raten": "2030-01-01"},
            {"Austrittsdatum": str(self.today)},
            {"Status": "haertefall"},
            {"Status": "bezahlt"},
            {"Status": "unbekannt"},
        ]:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                AssociationDepositImporter.import_opening_balance({**row, **change}, {})
            self.assertFalse(AssociationDeposit.objects.exists())
            self.assertFalse(Payment.objects.exists())

    def test_open_instalments_require_mandate_but_paid_balance_and_hardship_do_not(
        self,
    ):
        self.member.sepa_consent = None
        self.member.save()
        with self.assertRaisesMessage(ValidationError, "SEPA-Mandat"):
            AssociationDepositImporter.import_opening_balance(self.instalment_row(), {})
        self.assertFalse(AssociationDeposit.objects.exists())
        AssociationDepositImporter.import_opening_balance(self.row, {})
        self.assertFalse(Payment.objects.exists())

    def test_members_must_be_imported_first_using_stable_member_number(self):
        for number in ["", "missing", "999999999"]:
            with self.subTest(number=number), self.assertRaisesMessage(
                ValidationError, "zuerst die Mitglieder"
            ):
                AssociationDepositImporter.import_opening_balance(
                    {**self.row, "Mitgliedsnummer": number}, {}
                )
        self.assertFalse(AssociationDeposit.objects.exists())

    def test_extended_csv_command_dry_run_then_repeat_does_not_duplicate_payments(self):
        row = self.instalment_row()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "einlagen.csv"
            path.write_text(
                ";".join(row.keys()) + "\n" + ";".join(row.values()) + "\n",
                encoding="utf-8",
            )
            errors = io.StringIO()
            call_command(
                "import-data",
                type=["deposits"],
                file=[str(path)],
                dry_run=True,
                stdout=io.StringIO(),
                stderr=errors,
            )
            self.assertEqual("", errors.getvalue())
            self.assertFalse(AssociationDeposit.objects.exists())
            self.assertFalse(Payment.objects.exists())
            for _ in range(2):
                call_command(
                    "import-data",
                    type=["deposits"],
                    file=[str(path)],
                    stdout=io.StringIO(),
                    stderr=errors,
                )
            self.assertEqual("", errors.getvalue())
            self.assertEqual(2, Payment.objects.count())
            self.assertEqual(1, AssociationDeposit.objects.get().bookings.count())

    def test_repeat_after_export_does_not_recreate_collected_instalment(self):
        from tapir.associations.services.deposit_payment_exporter import (
            DepositPaymentExporter,
        )
        from tapir.wirgarten.tests.factories import ExportedFileFactory

        row = self.instalment_row()
        AssociationDepositImporter.import_opening_balance(row, {})
        with patch(
            "tapir.associations.services.deposit_payment_exporter.Pain008XmlStringGenerator.validate_single_payment"
        ), patch(
            "tapir.associations.services.deposit_payment_exporter.Pain008XmlStringGenerator.build_xml_string",
            return_value=b"<xml/>",
        ), patch(
            "tapir.associations.services.deposit_payment_exporter.export_file",
            side_effect=lambda **kwargs: ExportedFileFactory(),
        ):
            self.assertEqual([], DepositPaymentExporter.export(self.today, False, {}))
            self.assertEqual(
                MEMBER_IMPORT_STATUS_SKIPPED,
                AssociationDepositImporter.import_opening_balance(row, {}),
            )
            self.assertEqual([], DepositPaymentExporter.export(self.today, False, {}))
        self.assertEqual(
            1, Payment.objects.filter(status=Payment.PaymentStatus.PAID).count()
        )
        self.assertEqual(
            1, Payment.objects.filter(status=Payment.PaymentStatus.DUE).count()
        )
        deposit = AssociationDeposit.objects.get()
        collection_date = deposit.payments.get(
            status=Payment.PaymentStatus.PAID
        ).due_date
        self.assertEqual(
            Decimal("75.01"),
            AssociationDepositService.balances(deposit, {}, collection_date)["balance"],
        )
        self.assertEqual(1, deposit.bookings.count())

    def test_repeated_opening_balance_is_skipped_without_debit(self):
        self.assertEqual(
            MEMBER_IMPORT_STATUS_CREATED,
            AssociationDepositImporter.import_opening_balance(self.row, {}),
        )
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_opening_balance(self.row, {}),
        )
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(
            Decimal("200"),
            AssociationDepositService.balances(AssociationDeposit.objects.get(), {})[
                "balance"
            ],
        )
        with self.assertRaises(ValidationError):
            AssociationDepositImporter.import_opening_balance(
                {**self.row, "Betrag": "250"}, {}
            )
        with self.assertRaises(ValidationError):
            AssociationDepositImporter.import_opening_balance(
                {**self.row, "Buchungs-ID": "another-reference"}, {}
            )
        other = MemberFactory()
        with self.assertRaises(ValidationError):
            AssociationDepositImporter.import_opening_balance(
                {**self.row, "Mitgliedsnummer": str(other.member_no)}, {}
            )
        self.assertEqual(1, AssociationDeposit.objects.get().bookings.count())

    def test_import_dry_run_and_delete_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "einlagen.csv"
            path.write_text(
                ";".join(self.row.keys()) + "\n" + ";".join(self.row.values()) + "\n",
                encoding="utf-8",
            )
            call_command(
                "import-data",
                type=["deposits"],
                file=[str(path)],
                dry_run=True,
                stdout=io.StringIO(),
            )
            self.assertFalse(AssociationDeposit.objects.exists())
            call_command(
                "import-data", type=["deposits"], file=[str(path)], stdout=io.StringIO()
            )
            call_command(
                "import-data",
                type=["deposits"],
                file=[str(path)],
                update=["yes"],
                stdout=io.StringIO(),
            )
            self.assertEqual(1, AssociationDeposit.objects.get().bookings.count())
            with self.assertRaises(CommandError):
                call_command(
                    "import-data", type=["deposits"], file=[str(path)], delete_all=True
                )
            with self.assertRaises(CommandError):
                call_command("import-data", reset_all=True)

    def test_refund_report_contains_bank_details_and_excludes_settled_balance(self):
        AssociationDepositImporter.import_opening_balance(self.row, {})
        reference = datetime.datetime.combine(
            self.today, datetime.time(12), tzinfo=datetime.UTC
        )
        members = DepositReporting.refundable_members(reference)
        self.assertEqual([self.member.pk], list(members.values_list("pk", flat=True)))
        self.assertEqual(Decimal("200"), members.get().deposit_refundable)
        TemplateAssociationDepositRefunds.create_exports()
        csv = CsvExportBuilder.build_csv_export_string(
            CsvExport.objects.get(name=TemplateAssociationDepositRefunds.NAME),
            reference,
        )
        self.assertIn(self.member.iban, csv)
        self.assertIn(self.member.account_owner, csv)
        self.assertIn("200,00", csv)
        AssociationDepositService.apply(
            self.member,
            {
                "action": "refund",
                "amount": "200",
                "date": self.today,
                "note": "Bankbeleg 23",
            },
            "settlement-23",
            self.member,
            {},
            True,
        )
        self.assertFalse(DepositReporting.refundable_members(reference).exists())
        deposit = AssociationDeposit.objects.get()
        self.assertEqual(2, deposit.bookings.count())
        self.assertFalse(deposit.payments.exists())

    def test_filters_keep_pending_agreement_reduction_and_exemption_distinct(self):
        config = {
            **DepositConfiguration.get({}),
            "enabled": True,
            "allow_hardship": True,
        }
        with patch.object(DepositConfiguration, "get", return_value=config):
            AssociationDepositService.register(
                self.member, 0, True, True, self.today, self.member, {}
            )
            self.assertEqual(
                1,
                DepositReporting.filter_members(
                    Member.objects.all(), "pending", {}
                ).count(),
            )
            self.assertEqual(
                0,
                DepositReporting.filter_members(
                    Member.objects.all(), "exempt", {}
                ).count(),
            )
            AssociationDepositService.apply(
                self.member,
                {
                    "action": "agreement",
                    "amount": "100",
                    "note": "Zustimmung des Mitglieds dokumentiert",
                },
                "reduction",
                self.member,
                {},
                True,
            )
            self.assertEqual(
                0,
                DepositReporting.filter_members(
                    Member.objects.all(), "pending", {}
                ).count(),
            )
            self.assertEqual(
                1,
                DepositReporting.filter_members(
                    Member.objects.all(), "reduced", {}
                ).count(),
            )
            AssociationDepositService.apply(
                self.member,
                {
                    "action": "agreement",
                    "amount": "0",
                    "note": "Vollständiger Verzicht genehmigt und vereinbart",
                },
                "exemption",
                self.member,
                {},
                True,
            )
            self.assertEqual(
                1,
                DepositReporting.filter_members(
                    Member.objects.all(), "exempt", {}
                ).count(),
            )
            self.assertFalse(Payment.objects.exists())
            self.assertIn(
                "abgeschlossen",
                DepositReporting.status(
                    DepositReporting.annotate_members(Member.objects.all(), {}).get()
                ),
            )
