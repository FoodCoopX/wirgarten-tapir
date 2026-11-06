import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.associations.models import AssociationDepositPaymentCreatedLogEntry
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.tests.factories import AssociationDepositAccountFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.models import Member, Payment, MandateReference
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MandateReferenceFactory,
    PaymentFactory,
    PaymentTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositPayments(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.PAYMENT_DUE_DAY, 5)
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self.today = datetime.date(2026, 11, 5)
        self.member = MemberFactory()
        AssociationMembershipFactory(
            member=self.member, start_date=self.today, end_date=None
        )
        self.account = AssociationDepositAccountFactory(
            member=self.member, agreed_amount=Decimal("200"), effective_from=self.today
        )
        self.cache = {}

    def create_payment(self, member=None):
        return AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            member or self.member, actor=self.member, cache=self.cache
        )

    def receive(self, amount, reference="receipt-1"):
        return AssociationDepositReceiptRecorder.record_received_deposit(
            self.member,
            Decimal(amount),
            self.today,
            reference,
            "Kontoauszug",
            self.member,
            self.cache,
        )

    def test_receipt_before_payment_creation_reduces_amount_without_automatic_debit(
        self,
    ):
        self.receive("25")
        self.assertFalse(Payment.objects.exists())
        payment = self.create_payment()
        self.assertEqual(Decimal("175"), payment.amount)
        self.assertEqual(self.today, payment.due_date)
        self.assertIsNone(payment.transaction_id)
        self.assertEqual(self.member.pk, payment.mandate_ref.member_id)
        log = AssociationDepositPaymentCreatedLogEntry.objects.get()
        self.assertEqual(self.member.pk, log.actor_id)
        self.assertIn("175.00", log.render())

    def test_retry_reuses_payment_mandate_and_audit(self):
        payment = self.create_payment()
        self.cache = {}
        repeated = self.create_payment()
        self.assertEqual(payment.pk, repeated.pk)
        self.assertEqual(payment.updated_at, repeated.updated_at)
        self.assertEqual(1, Payment.objects.count())
        self.assertEqual(1, MandateReference.objects.count())
        self.assertEqual(1, AssociationDepositPaymentCreatedLogEntry.objects.count())

    def test_later_receipts_reduce_same_open_payment_and_retry_does_not_reduce_twice(
        self,
    ):
        payment = self.create_payment()
        self.receive("25")
        self.receive("25")
        payment.refresh_from_db()
        self.assertEqual(Decimal("175"), payment.amount)
        self.receive("50", "receipt-2")
        self.assertEqual(payment.pk, self.create_payment().pk)
        payment.refresh_from_db()
        self.assertEqual(Decimal("125"), payment.amount)
        self.assertEqual(1, Payment.objects.count())

    def test_full_external_receipt_removes_only_open_payment(self):
        payment = self.create_payment()
        self.receive("200")
        self.assertFalse(Payment.objects.filter(pk=payment.pk).exists())
        self.assertIsNone(self.create_payment())
        self.assertEqual(1, self.account.receipts.count())
        self.assertEqual(1, AssociationDepositPaymentCreatedLogEntry.objects.count())

    def test_fully_received_historical_amount_needs_no_mandate_or_payment(self):
        self.receive("200")
        self.assertIsNone(self.create_payment())
        self.assertFalse(MandateReference.objects.exists())
        self.assertFalse(Payment.objects.exists())

    def test_unknown_agreement_cannot_create_payment(self):
        with self.assertRaisesMessage(ValidationError, "Einlagenvereinbarung"):
            self.create_payment(member=MemberFactory())
        self.assertFalse(Payment.objects.exists())

    def test_missing_or_future_consent_is_rejected_using_fresh_member_data(self):
        for consent in [None, datetime.datetime(2026, 11, 6, tzinfo=datetime.UTC)]:
            with self.subTest(consent=consent):
                Member.objects.filter(pk=self.member.pk).update(sepa_consent=consent)
                with self.assertRaisesMessage(ValidationError, "SEPA-Zustimmung"):
                    self.create_payment()
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(MandateReference.objects.exists())

    def test_future_agreement_and_mandate_start_are_respected(self):
        self.account.effective_from = datetime.date(2026, 12, 10)
        self.account.save()
        mandate = MandateReferenceFactory(
            member=self.member,
            start_ts=datetime.datetime(2027, 1, 15, tzinfo=datetime.UTC),
        )
        payment = self.create_payment()
        self.assertEqual(mandate.pk, payment.mandate_ref_id)
        self.assertEqual(datetime.date(2027, 2, 5), payment.due_date)

    def test_after_collection_day_the_next_month_is_used(self):
        mock_timezone(self, datetime.datetime(2026, 11, 6, 12))
        self.assertEqual(datetime.date(2026, 12, 5), self.create_payment().due_date)

    def test_minimum_increase_does_not_change_agreed_total(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, "300")
        self.assertEqual(Decimal("200"), self.create_payment().amount)

    def test_exported_payment_and_files_survive_later_receipt_and_retry(self):
        payment = self.create_payment()
        transaction = PaymentTransactionFactory(type=payment.type, month=self.today)
        payment.status = Payment.PaymentStatus.PAID
        payment.transaction = transaction
        payment.due_date = datetime.date(2026, 12, 5)
        payment.save()
        original = list(self.account.payments.values())
        csv_bytes = bytes(transaction.csv_file.file)

        self.receive("25")
        self.assertIsNone(self.create_payment())
        self.assertEqual(original, list(self.account.payments.values()))
        transaction.csv_file.refresh_from_db()
        self.assertEqual(csv_bytes, bytes(transaction.csv_file.file))
        self.assertEqual(Decimal("25"), self.account.receipts.get().amount)

    def test_paid_status_without_transaction_is_also_immutable(self):
        payment = self.create_payment()
        Payment.objects.filter(pk=payment.pk).update(status=Payment.PaymentStatus.PAID)
        self.receive("25")
        self.assertIsNone(self.create_payment())
        payment.refresh_from_db()
        self.assertEqual(Decimal("200"), payment.amount)

    def test_ambiguous_multiple_open_payments_are_rejected_without_changes(self):
        payment = self.create_payment()
        PaymentFactory(
            association_deposit_account=self.account,
            mandate_ref=payment.mandate_ref,
            amount=1,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
            type=payment.type,
        )
        before = list(self.account.payments.values())
        with self.assertRaisesMessage(ValidationError, "mehrere offene"):
            self.create_payment()
        self.assertEqual(before, list(self.account.payments.values()))
