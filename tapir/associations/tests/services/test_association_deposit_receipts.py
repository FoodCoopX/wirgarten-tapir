import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositReceipt,
    AssociationDepositReceiptCreatedLogEntry,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.services.association_deposit_receipt_total_calculator import (
    AssociationDepositReceiptTotalCalculator,
)
from tapir.associations.tests.factories import AssociationDepositReceiptFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION, LEGAL_STATUS_COOPERATIVE
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositReceipts(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        mock_timezone(self, datetime.datetime(2026, 11, 5))
        self.member = MemberFactory()
        self.admin = MemberFactory(is_superuser=True)
        self.cache = {}
        self.today = datetime.date(2026, 11, 5)

    def record_receipt(self, **changes):
        arguments = {
            "member": self.member,
            "amount": Decimal("25.00"),
            "received_on": self.today,
            "reference": "bank-statement-123",
            "note": "Extern eingegangen laut Kontoauszug",
            "actor": self.admin,
            "cache": self.cache,
        }
        arguments.update(changes)
        return AssociationDepositReceiptRecorder.record_received_deposit(**arguments)

    def test_receipt_below_minimum_is_recorded_with_audit_and_without_debit(self):
        receipt = self.record_receipt()

        self.assertEqual(self.member, receipt.account.member)
        self.assertEqual(Decimal("25.00"), receipt.amount)
        self.assertEqual(self.today, receipt.received_on)
        self.assertFalse(Payment.objects.exists())
        log = AssociationDepositReceiptCreatedLogEntry.objects.get()
        self.assertEqual(self.admin.pk, log.actor_id)
        self.assertEqual(self.member.pk, log.user_id)
        self.assertEqual(receipt.pk, log.values["id"])
        self.assertIn(receipt.reference, log.render())
        self.assertIn(receipt.note, log.render())

    def test_identical_retry_keeps_one_receipt_and_original_audit(self):
        first = self.record_receipt()
        repeated = self.record_receipt(actor=None, cache={})

        self.assertEqual(first.pk, repeated.pk)
        self.assertEqual(1, AssociationDepositAccount.objects.count())
        self.assertEqual(1, AssociationDepositReceipt.objects.count())
        self.assertEqual(1, AssociationDepositReceiptCreatedLogEntry.objects.count())
        self.assertEqual(
            self.admin.pk,
            AssociationDepositReceiptCreatedLogEntry.objects.get().actor_id,
        )

    def test_conflicting_retry_is_rejected_without_changing_history(self):
        first = self.record_receipt()
        for changes in [
            {"amount": Decimal("30")},
            {"received_on": self.today - datetime.timedelta(days=1)},
            {"note": "Anderer Beleg"},
            {"member": self.admin},
        ]:
            with self.subTest(changes=changes), self.assertRaisesMessage(
                ValidationError, "abweichenden Daten"
            ):
                self.record_receipt(**changes)
        first.refresh_from_db()
        self.assertEqual(Decimal("25"), first.amount)
        self.assertEqual(1, AssociationDepositAccount.objects.count())
        self.assertEqual(1, AssociationDepositReceipt.objects.count())
        self.assertEqual(1, AssociationDepositReceiptCreatedLogEntry.objects.count())

    def test_invalid_receipt_creates_no_account_or_audit(self):
        for changes in [
            {"amount": Decimal("0")},
            {"amount": Decimal("-1")},
            {"amount": Decimal("25.001")},
            {"received_on": self.today + datetime.timedelta(days=1)},
            {"reference": " "},
            {"reference": "x" * 101},
            {"note": " "},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.record_receipt(**changes)
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(AssociationDepositReceipt.objects.exists())
        self.assertFalse(AssociationDepositReceiptCreatedLogEntry.objects.exists())

    def test_cooperative_receipt_is_rejected(self):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_COOPERATIVE
        )
        with self.assertRaisesMessage(ValidationError, "nur für Vereine"):
            self.record_receipt()
        self.assertFalse(AssociationDepositAccount.objects.exists())

    def test_audit_failure_rolls_back_account_and_receipt(self):
        with patch.object(
            AssociationDepositReceiptCreatedLogEntry,
            "save",
            side_effect=RuntimeError("Audit nicht verfügbar"),
        ):
            with self.assertRaises(RuntimeError):
                self.record_receipt()
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(AssociationDepositReceipt.objects.exists())

    def test_reference_collision_after_initial_lookup_returns_existing_receipt(self):
        receipt = self.record_receipt()
        with patch.object(
            AssociationDepositReceipt.objects, "select_related"
        ) as lookup:
            # A competing request has stored the reference after our initial lookup.
            lookup.return_value.filter.return_value.first.side_effect = [None, receipt]
            repeated = self.record_receipt()

        self.assertEqual(receipt.pk, repeated.pk)
        self.assertEqual(1, AssociationDepositReceipt.objects.count())
        self.assertEqual(1, AssociationDepositReceiptCreatedLogEntry.objects.count())

    def test_reference_collision_for_another_member_rolls_back_empty_account(self):
        receipt = self.record_receipt()
        with patch.object(
            AssociationDepositReceipt.objects, "select_related"
        ) as lookup:
            lookup.return_value.filter.return_value.first.side_effect = [None, receipt]
            with self.assertRaisesMessage(ValidationError, "abweichenden Daten"):
                self.record_receipt(member=self.admin)

        self.assertEqual(1, AssociationDepositAccount.objects.count())
        self.assertEqual(1, AssociationDepositReceipt.objects.count())
        self.assertEqual(1, AssociationDepositReceiptCreatedLogEntry.objects.count())

    def test_unrelated_database_failure_is_not_treated_as_a_retry(self):
        with patch.object(
            AssociationDepositReceipt.objects,
            "create",
            side_effect=IntegrityError("Speichern fehlgeschlagen"),
        ):
            with self.assertRaises(IntegrityError):
                self.record_receipt()
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(AssociationDepositReceiptCreatedLogEntry.objects.exists())

    def test_total_is_member_specific_and_respects_historical_date(self):
        earlier = self.today - datetime.timedelta(days=30)
        self.record_receipt(received_on=earlier, amount=Decimal("100.01"), actor=None)
        self.record_receipt(reference="bank-statement-124", amount=Decimal("25.02"))
        AssociationDepositReceiptFactory(amount=900, received_on=earlier)

        self.assertEqual(
            Decimal("100.01"),
            AssociationDepositReceiptTotalCalculator.get_received_deposit_total(
                self.member, self.cache, earlier
            ),
        )
        self.assertEqual(
            Decimal("125.03"),
            AssociationDepositReceiptTotalCalculator.get_received_deposit_total(
                self.member, self.cache
            ),
        )
        self.assertEqual(
            1, AssociationDepositAccount.objects.filter(member=self.member).count()
        )
        self.assertFalse(Payment.objects.exists())

    def test_reading_total_does_not_create_an_account_and_is_fresh_after_booking(self):
        self.assertEqual(
            Decimal("0"),
            AssociationDepositReceiptTotalCalculator.get_received_deposit_total(
                self.member, self.cache
            ),
        )
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.record_receipt()
        self.assertEqual(
            Decimal("25"),
            AssociationDepositReceiptTotalCalculator.get_received_deposit_total(
                self.member, self.cache
            ),
        )

    def test_database_enforces_positive_amount_and_unique_reference(self):
        receipt = self.record_receipt()
        for changes in [
            {"amount": 0, "reference": "zero"},
            {"reference": receipt.reference},
        ]:
            with self.subTest(changes=changes), self.assertRaises(
                IntegrityError
            ), transaction.atomic():
                AssociationDepositReceiptFactory(account=receipt.account, **changes)

    def test_account_and_member_with_receipt_cannot_be_deleted(self):
        receipt = self.record_receipt()
        for instance in [receipt.account, self.member]:
            with self.subTest(instance=instance.pk), self.assertRaises(ProtectedError):
                instance.delete()
        self.assertTrue(
            AssociationDepositReceipt.objects.filter(pk=receipt.pk).exists()
        )

    def test_audit_escapes_user_supplied_text(self):
        self.record_receipt(note="<script>alert(1)</script>")

        html = AssociationDepositReceiptCreatedLogEntry.objects.get().render()
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
