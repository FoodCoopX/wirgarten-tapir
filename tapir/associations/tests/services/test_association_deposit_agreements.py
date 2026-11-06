import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositAgreementCreatedLogEntry,
)
from tapir.associations.services.association_deposit_agreement_creator import (
    AssociationDepositAgreementCreator,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.services.association_deposit_remaining_amount_calculator import (
    AssociationDepositRemainingAmountCalculator,
)
from tapir.core.config import LEGAL_STATUS_ASSOCIATION, LEGAL_STATUS_COOPERATIVE
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositAgreements(TapirIntegrationTest):
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
        self.today = datetime.date(2026, 11, 5)
        self.cache = {}

    def create_agreement(self, **changes):
        arguments = dict(
            member=self.member,
            amount=Decimal("200.00"),
            effective_from=self.today,
            actor=self.admin,
            cache=self.cache,
        )
        arguments.update(changes)
        return AssociationDepositAgreementCreator.create_regular_agreement(**arguments)

    def record_receipt(self, amount, reference="received-1"):
        return AssociationDepositReceiptRecorder.record_received_deposit(
            member=self.member,
            amount=Decimal(amount),
            received_on=self.today,
            reference=reference,
            note="Zahlungseingang laut Kontoauszug",
            actor=self.admin,
            cache=self.cache,
        )

    def remaining_amount(self):
        return AssociationDepositRemainingAmountCalculator.get_remaining_deposit_amount(
            self.member, cache=self.cache
        )

    def test_regular_agreement_is_recorded_with_audit_without_payment(self):
        account = self.create_agreement()

        self.assertEqual(Decimal("200"), account.agreed_amount)
        self.assertEqual(self.today, account.effective_from)
        self.assertEqual(Decimal("200"), self.remaining_amount())
        log = AssociationDepositAgreementCreatedLogEntry.objects.get()
        self.assertEqual(self.admin.pk, log.actor_id)
        self.assertEqual(self.member.pk, log.user_id)
        self.assertEqual(account.pk, log.values["id"])
        self.assertIn("200.00", log.render())
        self.assertFalse(Payment.objects.exists())

    def test_received_amounts_reduce_remainder_before_and_after_agreement(self):
        receipt = self.record_receipt("25")
        account = self.create_agreement()
        self.assertEqual(receipt.account_id, account.pk)
        self.assertEqual(Decimal("175"), self.remaining_amount())

        self.record_receipt("50", "received-2")
        self.assertEqual(Decimal("125"), self.remaining_amount())
        self.create_agreement(cache={})
        self.assertEqual(Decimal("125"), self.remaining_amount())
        self.assertEqual(2, account.receipts.count())
        self.assertFalse(Payment.objects.exists())

    def test_identical_retry_preserves_original_audit_and_account(self):
        first = self.create_agreement()
        repeated = self.create_agreement(actor=None, cache={})

        self.assertEqual(first.pk, repeated.pk)
        self.assertEqual(first.updated_at, repeated.updated_at)
        self.assertEqual(1, AssociationDepositAccount.objects.count())
        self.assertEqual(1, AssociationDepositAgreementCreatedLogEntry.objects.count())
        self.assertEqual(
            self.admin.pk,
            AssociationDepositAgreementCreatedLogEntry.objects.get().actor_id,
        )

    def test_retry_after_minimum_increase_and_next_day_keeps_original_agreement(self):
        account = self.create_agreement()
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, "300.00")
        mock_timezone(self, datetime.datetime(2026, 11, 6))

        repeated = self.create_agreement(cache={})
        self.assertEqual(account.pk, repeated.pk)
        self.assertEqual(Decimal("200"), self.remaining_amount())
        self.assertEqual(1, AssociationDepositAgreementCreatedLogEntry.objects.count())
        self.assertFalse(Payment.objects.exists())

    def test_conflicting_agreement_is_rejected_without_overwriting_existing_amount(
        self,
    ):
        self.create_agreement()
        for changes in [
            {"amount": Decimal("250")},
            {"effective_from": self.today + datetime.timedelta(days=1)},
        ]:
            with self.subTest(changes=changes), self.assertRaisesMessage(
                ValidationError, "abweichende"
            ):
                self.create_agreement(**changes)
        self.assertEqual(Decimal("200"), self.remaining_amount())
        self.assertEqual(1, AssociationDepositAgreementCreatedLogEntry.objects.count())

    def test_invalid_regular_agreement_does_not_leave_an_account(self):
        for changes in [
            {"amount": Decimal("0")},
            {"amount": Decimal("100")},
            {"amount": Decimal("225")},
            {"amount": Decimal("NaN")},
            {"amount": Decimal("200.001")},
            {"effective_from": self.today - datetime.timedelta(days=1)},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.create_agreement(**changes)
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(AssociationDepositAgreementCreatedLogEntry.objects.exists())

    def test_future_agreement_keeps_start_date_without_creating_payment(self):
        start = self.today + datetime.timedelta(days=90)
        account = self.create_agreement(effective_from=start)
        self.assertEqual(start, account.effective_from)
        self.assertFalse(Payment.objects.exists())

    def test_without_agreement_remainder_is_unknown_even_with_existing_receipt(self):
        self.assertIsNone(self.remaining_amount())
        self.assertFalse(AssociationDepositAccount.objects.exists())
        receipt = self.record_receipt("25")
        self.assertIsNone(self.remaining_amount())
        receipt.refresh_from_db()
        self.assertEqual(Decimal("25"), receipt.amount)
        self.assertFalse(AssociationDepositAgreementCreatedLogEntry.objects.exists())

    def test_full_and_excess_receipts_leave_zero_remainder_without_changing_receipts(
        self,
    ):
        account = self.create_agreement()
        self.record_receipt("200")
        self.assertEqual(Decimal("0"), self.remaining_amount())
        self.record_receipt("25", "excess")
        self.assertEqual(Decimal("0"), self.remaining_amount())
        self.assertEqual(2, account.receipts.count())
        self.assertFalse(Payment.objects.exists())

    def test_cooperative_agreement_is_rejected(self):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_COOPERATIVE
        )
        with self.assertRaisesMessage(ValidationError, "nur für Vereine"):
            self.create_agreement()
        self.assertFalse(AssociationDepositAccount.objects.exists())

    def test_audit_failure_rolls_back_agreement_and_preserves_existing_receipt(self):
        receipt = self.record_receipt("25")
        with patch.object(
            AssociationDepositAgreementCreatedLogEntry,
            "save",
            side_effect=RuntimeError("Audit nicht verfügbar"),
        ):
            with self.assertRaises(RuntimeError):
                self.create_agreement()
        receipt.account.refresh_from_db()
        self.assertIsNone(receipt.account.agreed_amount)
        self.assertIsNone(receipt.account.effective_from)
        self.assertEqual(1, receipt.account.receipts.count())
        self.assertFalse(AssociationDepositAgreementCreatedLogEntry.objects.exists())

    def test_database_rejects_half_filled_agreement_on_insert_and_update(self):
        invalid_values = [
            dict(agreed_amount=None, effective_from=self.today),
            dict(agreed_amount=Decimal("200"), effective_from=None),
        ]
        for values in invalid_values:
            with self.subTest(operation="insert", values=values), self.assertRaises(
                IntegrityError
            ), transaction.atomic():
                AssociationDepositAccount.objects.create(member=self.member, **values)
        account = AssociationDepositAccount.objects.create(member=self.member)
        for values in invalid_values:
            with self.subTest(operation="update", values=values), self.assertRaises(
                IntegrityError
            ), transaction.atomic():
                AssociationDepositAccount.objects.filter(pk=account.pk).update(**values)
        account.refresh_from_db()
        self.assertIsNone(account.agreed_amount)
        self.assertIsNone(account.effective_from)

    def test_database_allows_both_empty_or_both_complete_agreement_fields(self):
        account = AssociationDepositAccount.objects.create(member=self.member)
        AssociationDepositAccount.objects.filter(pk=account.pk).update(
            agreed_amount=Decimal("200"), effective_from=self.today
        )
        account.refresh_from_db()
        self.assertEqual(Decimal("200"), account.agreed_amount)
        self.assertEqual(self.today, account.effective_from)
        AssociationDepositAccount.objects.filter(pk=account.pk).update(
            agreed_amount=None, effective_from=None
        )
        self.assertIsNone(self.remaining_amount())

    def test_explicit_zero_is_distinct_from_no_agreement_on_read(self):
        account = AssociationDepositAccount.objects.create(member=self.member)
        self.assertIsNone(self.remaining_amount())
        AssociationDepositAccount.objects.filter(pk=account.pk).update(
            agreed_amount=Decimal("0"), effective_from=self.today
        )
        self.assertEqual(Decimal("0"), self.remaining_amount())
