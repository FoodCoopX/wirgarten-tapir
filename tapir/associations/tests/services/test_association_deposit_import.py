import csv
import datetime
import io
from decimal import Decimal
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.core.management.base import OutputWrapper
from django.template.loader import render_to_string

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositImportedLogEntry,
    AssociationDepositReceipt,
    AssociationMembership,
)
from tapir.associations.services.association_deposit_agreement_authorizer import (
    AssociationDepositAgreementAuthorizer,
)
from tapir.associations.services.association_deposit_importer import (
    AssociationDepositImporter,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_refund_recorder import (
    AssociationDepositRefundRecorder,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.log.models import LogEntry
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
)
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.member_importer import MemberImporter
from tapir.wirgarten.models import (
    Member,
    Payment,
    PaymentTransaction,
    ExportedFile,
    MandateReference,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositImport(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.today = datetime.date(2026, 11, 5)
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        for key, value in {
            ParameterKeys.ORGANISATION_LEGAL_STATUS: LEGAL_STATUS_ASSOCIATION,
            ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED: True,
            ParameterKeys.PAYMENT_DUE_DAY: 5,
            ParameterKeys.PAYMENT_START_DATE: datetime.date(2026, 1, 1),
            ParameterKeys.PAYMENT_ORGANISATION_IBAN: "NL88ABNA2011060885",
            ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER: "DE98ZZZ09999999999",
            ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM: False,
        }.items():
            self._set_parameter(key, value)
        self.member = self.make_member()

    def make_member(self):
        member = MemberFactory(
            iban="NL88ABNA2011060885",
            account_owner="Test Mitglied",
            sepa_consent=datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc),
        )
        AssociationMembershipFactory(
            member=member, start_date=datetime.date(2026, 1, 1)
        )
        return member

    def row(self, member=None, **changes):
        data = {
            "Nr": str((member or self.member).member_no),
            "Einlage Status": "vereinbart",
            "Einlage Gesamt": "200",
            "Einlage Erhalten": "200",
            "Einlage Stichtag": "2026-11-05",
            "Einlage Beginn": "2026-09-01",
            "Einlage Ratenzahl": "1",
            "Einlage Offene Raten": "",
            "Einlage Individuell": "nein",
            "Einlage Anfrage": "",
            "Einlage Beleg": "Geprüfter Altbestand",
        }
        data.update(changes)
        return data

    def history(self):
        return {
            model._meta.label: list(model.objects.order_by("pk").values())
            for model in [
                AssociationDepositAccount,
                AssociationDepositReceipt,
                Payment,
                PaymentTransaction,
                ExportedFile,
                MandateReference,
                LogEntry,
            ]
        }

    def command(self, rows, *arguments):
        out, err = io.StringIO(), io.StringIO()
        with NamedTemporaryFile(mode="w", suffix=".csv", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]), delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
            file.flush()
            call_command(
                "import-data",
                "--type",
                "deposits",
                "--file",
                file.name,
                *arguments,
                stdout=out,
                stderr=err
            )
        return out.getvalue(), err.getvalue()

    def test_paid_opening_never_creates_a_second_debit_and_repeat_is_noop(self):
        row = self.row()
        self.assertEqual(
            MEMBER_IMPORT_STATUS_CREATED,
            AssociationDepositImporter.import_deposit(row, {}),
        )
        self.assertEqual(200, AssociationDepositReceipt.objects.get().amount)
        audit = AssociationDepositImportedLogEntry.objects.get()
        rendered = render_to_string(audit.template_name, {"entry": audit})
        self.assertIn("05.11.2026", rendered)
        self.assertIn("Vereinbarung: 200,00 €", rendered)
        self.assertIn("erhalten: 200,00 €", rendered)
        self.assertIn("offene Raten: 0", rendered)
        self.assertIn("Geprüfter Altbestand", rendered)
        self.assertNotIn("snapshot", rendered)
        self.assertNotIn('"state":', rendered)
        self.assertFalse(Payment.objects.exists())
        before = self.history()
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_deposit(row, {}),
        )
        self.assertEqual(before, self.history())
        PaymentExportBuilder.export_association_deposit_payments(self.today, False, {})
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_exact_supplied_four_rates_cannot_export_before_november_twenty(self):
        row = self.row(
            **{
                "Einlage Erhalten": "0",
                "Einlage Ratenzahl": "4",
                "Einlage Offene Raten": "2026-11-20:50|2026-12-20:50|2027-01-20:50|2027-02-20:50",
            }
        )
        AssociationDepositImporter.import_deposit(row, {})
        self.assertEqual(
            [
                datetime.date(2026, 11, 20),
                datetime.date(2026, 12, 20),
                datetime.date(2027, 1, 20),
                datetime.date(2027, 2, 20),
            ],
            list(
                Payment.objects.order_by("due_date").values_list("due_date", flat=True)
            ),
        )
        PaymentExportBuilder.export_association_deposit_payments(self.today, False, {})
        self.assertFalse(PaymentTransaction.objects.exists())
        self.assertEqual(
            4, Payment.objects.filter(status=Payment.PaymentStatus.DUE).count()
        )

    def test_remaining_two_rates_and_replay_after_export_and_new_terms_preserve_history(
        self,
    ):
        row = self.row(
            **{
                "Einlage Erhalten": "100",
                "Einlage Ratenzahl": "4",
                "Einlage Offene Raten": "2026-11-20:50|2026-12-20:50",
            }
        )
        AssociationDepositImporter.import_deposit(row, {})
        self.assertEqual(
            [(3, Decimal("50")), (4, Decimal("50"))],
            list(
                Payment.objects.order_by("due_date").values_list(
                    "instalment_number", "amount"
                )
            ),
        )
        mock_timezone(self, datetime.datetime(2026, 11, 20, 12))
        PaymentExportBuilder.export_association_deposit_payments(
            datetime.date(2026, 11, 20), False, {}
        )
        self.assertEqual(
            1, Payment.objects.filter(status=Payment.PaymentStatus.PAID).count()
        )
        before = self.history()
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_deposit(row, {}),
        )
        self.assertEqual(before, self.history())
        account = AssociationDepositAccount.objects.get()
        admin = MemberFactory(is_superuser=True)
        AssociationDepositAgreementAuthorizer.authorize_agreement(
            member=self.member,
            amount=Decimal("175"),
            effective_from=datetime.date(2026, 11, 20),
            instalment_count=1,
            consented_on=self.today,
            consent_note="Neue dokumentierte Vereinbarung",
            expected_revision=account.agreement_revision,
            request_key="3e2e3717-dcf2-4e12-ae7c-4a226ee051a7",
            actor=admin,
            cache={},
        )
        before = self.history()
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_deposit(row, {}),
        )
        self.assertEqual(before, self.history())
        self.assertEqual(175, AssociationDepositAccount.objects.get().agreed_amount)

    def test_pending_request_keeps_unknown_total_and_received_credit_without_notifications(
        self,
    ):
        row = self.row(
            **{
                "Einlage Status": "offen",
                "Einlage Gesamt": "",
                "Einlage Erhalten": "25",
                "Einlage Beginn": "",
                "Einlage Anfrage": "2026-11-01T10:00:00+01:00",
            }
        )
        with patch(
            "tapir.associations.services.association_deposit_hardship_notifier.send_email"
        ) as notify:
            AssociationDepositImporter.import_deposit(row, {})
            notify.assert_not_called()
        account = AssociationDepositAccount.objects.get()
        self.assertIsNone(account.agreed_amount)
        self.assertIsNone(account.effective_from)
        self.assertEqual(
            datetime.date(2026, 11, 1), account.hardship_requested_at.date()
        )
        self.assertEqual(25, account.receipts.get().amount)
        self.assertFalse(Payment.objects.exists())
        audit = AssociationDepositImportedLogEntry.objects.get()
        rendered = render_to_string(audit.template_name, {"entry": audit})
        self.assertIn("Nicht vereinbart", rendered)
        self.assertNotIn("None", rendered)
        before = self.history()
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_deposit(row, {}),
        )
        self.assertEqual(before, self.history())

    def test_reduced_total_cents_and_explicit_zero_waiver_do_not_create_difference_claim(
        self,
    ):
        row = self.row(
            **{
                "Einlage Gesamt": "100",
                "Einlage Erhalten": "25",
                "Einlage Ratenzahl": "4",
                "Einlage Offene Raten": "2026-11-20:18,75|2026-12-20:18,75|2027-01-20:18,75|2027-02-20:18,75",
                "Einlage Individuell": "ja",
            }
        )
        AssociationDepositImporter.import_deposit(row, {})
        account = AssociationDepositAccount.objects.get(member=self.member)
        self.assertTrue(account.is_individual_agreement)
        self.assertEqual(100, account.agreed_amount)
        self.assertEqual(
            [Decimal("18.75")] * 4,
            list(account.payments.values_list("amount", flat=True)),
        )
        waived = self.make_member()
        AssociationDepositImporter.import_deposit(
            self.row(
                waived,
                **{
                    "Einlage Gesamt": "0",
                    "Einlage Erhalten": "25",
                    "Einlage Individuell": "ja",
                }
            ),
            {},
        )
        waiver = AssociationDepositAccount.objects.get(member=waived)
        self.assertEqual(0, waiver.agreed_amount)
        self.assertFalse(waiver.payments.exists())

    def test_conflicting_snapshot_never_touches_keycloak_or_any_financial_history(self):
        row = self.row()
        AssociationDepositImporter.import_deposit(row, {})
        before = self.history()
        self.mock_keycloak_client.reset_mock()
        with self.assertRaisesMessage(ValidationError, "Abweichender"):
            AssociationDepositImporter.import_deposit(
                {**row, "Einlage Erhalten": "250"}, {}
            )
        self.mock_keycloak_client.update_user.assert_not_called()
        self.mock_keycloak_client.create_user.assert_not_called()
        self.assertEqual(before, self.history())

    def test_repeat_preserves_refund_hold_and_changed_membership_phases(self):
        row = self.row()
        AssociationDepositImporter.import_deposit(row, {})
        admin = MemberFactory(is_superuser=True)
        AssociationDepositRefundRecorder.record_external_refund(
            self.member,
            Decimal("50"),
            self.today,
            "external-return",
            "Beleg",
            True,
            1,
            Decimal("0"),
            admin,
            {},
        )
        membership = AssociationMembership.objects.get(member=self.member)
        AssociationMembershipChangeHandler.set_end_date(
            membership, datetime.date(2026, 11, 1), admin, {}
        )
        AssociationMembershipChangeHandler.start_membership(
            self.member, membership.type, self.today, admin, {}
        )
        before = self.history()
        self.assertEqual(
            MEMBER_IMPORT_STATUS_SKIPPED,
            AssociationDepositImporter.import_deposit(row, {}),
        )
        self.assertEqual(before, self.history())
        self.assertTrue(
            AssociationDepositAccount.objects.get().refund_requires_agreement
        )

    def test_invalid_plans_and_unknown_members_fail_without_any_financial_write(self):
        cases = [
            {"Einlage Erhalten": "100"},
            {"Einlage Gesamt": "0", "Einlage Erhalten": "0", "Einlage Ratenzahl": "4"},
            {
                "Einlage Erhalten": "0",
                "Einlage Beginn": "2026-11-20",
                "Einlage Offene Raten": "2026-11-05:200",
            },
            {"Einlage Erhalten": "0", "Einlage Offene Raten": "2026-11-20:199.999"},
            {"Einlage Ratenzahl": "13"},
            {"Nr": "99999999"},
            {"Einlage Rückzahlungen": "50"},
        ]
        before = self.history()
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                AssociationDepositImporter.import_deposit(self.row(**changes), {})
            self.assertEqual(before, self.history())
        PaymentExportBuilder.export_association_deposit_payments(self.today, False, {})
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_csv_dry_run_repeat_and_conflict_use_existing_command(self):
        row = self.row()
        before = self.history()
        out, err = self.command([row], "--dry-run")
        self.assertEqual("", err)
        self.assertIn("Created: 1", out)
        self.assertEqual(before, self.history())
        out, err = self.command([row])
        self.assertEqual("", err)
        before = self.history()
        out, err = self.command([row], "--update", "yes")
        self.assertIn("Skipped: 1", out)
        self.assertEqual(before, self.history())
        out, err = self.command([{**row, "Einlage Erhalten": "250"}])
        self.assertIn("Abweichender", err)
        self.assertEqual(before, self.history())
        with self.assertRaises(CommandError):
            self.command([row], "--delete-all")

    def test_failed_row_clears_rolled_back_mandate_before_identical_next_row(self):
        row = self.row(
            **{"Einlage Erhalten": "0", "Einlage Offene Raten": "2026-11-20:200"}
        )
        original = AssociationDepositPaymentSynchronizer._create_payment_plan
        calls = 0

        def fail_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            value = original(*args, **kwargs)
            if calls == 1:
                raise ValidationError("Simulierter Fehler nach Mandatsanlage")
            return value

        with patch.object(
            AssociationDepositPaymentSynchronizer,
            "_create_payment_plan",
            side_effect=fail_once,
        ):
            out, err = self.command([row, row])
        self.assertIn("Created: 1", out)
        self.assertIn("Simulierter Fehler", err)
        self.assertEqual(1, AssociationDepositAccount.objects.count())
        self.assertEqual(1, Payment.objects.count())
        self.assertEqual(1, MandateReference.objects.count())
        self.assertEqual(1, AssociationDepositImportedLogEntry.objects.count())

    def profile_row(self, **changes):
        row = {
            "Nr": str(self.member.member_no),
            "Vorname": self.member.first_name,
            "Nachname": self.member.last_name,
            "Mailadresse": self.member.email,
            "IBAN": self.member.iban,
            "Kontoinhaber": self.member.account_owner,
        }
        row.update(changes)
        return row

    def test_profile_only_import_preserves_all_membership_history_and_hold(self):
        AssociationDepositImporter.import_deposit(self.row(), {})
        membership = AssociationMembership.objects.get(member=self.member)
        membership.end_date = datetime.date(2026, 3, 31)
        membership.save()
        AssociationMembershipFactory(
            member=self.member, start_date=datetime.date(2026, 5, 1)
        )
        before = list(
            AssociationMembership.objects.filter(member=self.member)
            .order_by("pk")
            .values()
        )
        account_before = self.history()[AssociationDepositAccount._meta.label]
        MemberImporter.import_member(
            self.profile_row(Vorname="Neuer Vorname"),
            True,
            False,
            OutputWrapper(io.StringIO()),
        )
        self.assertEqual(
            before,
            list(
                AssociationMembership.objects.filter(member=self.member)
                .order_by("pk")
                .values()
            ),
        )
        self.assertEqual(
            account_before, self.history()[AssociationDepositAccount._meta.label]
        )

    def test_conflicting_membership_or_mixed_money_fields_rejected_before_profile_keycloak_changes(
        self,
    ):
        AssociationDepositImporter.import_deposit(self.row(), {})
        self.member.keycloak_id = "synthetic-keycloak"
        self.member.save()
        self.mock_keycloak_client.reset_mock()
        before = list(Member.objects.filter(pk=self.member.pk).values())
        for changes in [
            {"Vereinsmitgliedschafttyp": "Unbekannter Typ"},
            {"Vereinsmitgliedschaft End_Date": "2026-12-31"},
            {"Einlage Erhalten": "250"},
        ]:
            with self.subTest(changes=changes), self.assertRaises(
                TapirDataImportException
            ):
                MemberImporter.import_member(
                    self.profile_row(Mailadresse="changed@example.test", **changes),
                    True,
                    False,
                    OutputWrapper(io.StringIO()),
                )
            self.assertEqual(
                before, list(Member.objects.filter(pk=self.member.pk).values())
            )
        self.mock_keycloak_client.update_user.assert_not_called()
