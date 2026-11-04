import datetime

from tapir.coop.models import (
    CoopSharesCancelledDuringTrialLogEntry,
)
from tapir.coop.services.coop_membership_cancellation_manager import (
    CoopMembershipCancellationManager,
)
from tapir.wirgarten.models import CoopShareTransaction, Payment
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    CoopShareTransactionFactory,
    PaymentFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCancelCoopMembership(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, datetime.datetime(year=2024, month=9, day=27))

    def test_cancelCoopMembership_default_deletesAllFutureSharePurchasesAndCreatesLogEntry(
        self,
    ):
        member = MemberFactory.create()
        actor = MemberFactory.create()

        transaction_1 = CoopShareTransactionFactory.create(  # transaction in the past, should not be deleted
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.date(year=2024, month=9, day=26),
        )
        transaction_2 = CoopShareTransactionFactory.create(  # is not a purchase, should not be deleted
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
            valid_at=datetime.date(year=2024, month=9, day=28),
            quantity=-1,
        )
        transaction_3 = CoopShareTransactionFactory.create(  # should get deleted
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.date(year=2024, month=9, day=28),
        )

        CoopMembershipCancellationManager.cancel_coop_membership(
            member=member, actor=actor
        )

        self.assertEqual(2, CoopShareTransaction.objects.count())
        self.assertIn(transaction_1, CoopShareTransaction.objects.all())
        self.assertIn(transaction_2, CoopShareTransaction.objects.all())

        self.assertEqual(1, CoopSharesCancelledDuringTrialLogEntry.objects.count())
        log_entry = CoopSharesCancelledDuringTrialLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)
        self.assertEqual(transaction_3.quantity, log_entry.nb_shares)
        self.assertEqual(
            transaction_3.valid_at, log_entry.shares_would_have_been_valid_at
        )

    def test_cancelCoopMembership_paymentNotExportedYet_paymentDeleted(self):
        member = MemberFactory.create()
        cancelled_transaction = CoopShareTransactionFactory.create(
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.datetime(year=2024, month=9, day=28),
        )
        unexported_payment = PaymentFactory.create(
            mandate_ref__member=member,
            coop_share_transaction=cancelled_transaction,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
        )
        transaction_of_other_member = CoopShareTransactionFactory.create(
            valid_at=datetime.datetime(year=2024, month=9, day=28),
        )
        payment_of_other_member = PaymentFactory.create(
            mandate_ref__member=transaction_of_other_member.member,
            coop_share_transaction=transaction_of_other_member,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
        )

        CoopMembershipCancellationManager.cancel_coop_membership(member)

        self.assertFalse(Payment.objects.filter(id=unexported_payment.id).exists())
        self.assertTrue(Payment.objects.filter(id=payment_of_other_member.id).exists())

    def test_cancelCoopMembership_paymentAlreadyExported_paymentKeptAndUnlinked(self):
        # The monthly export runs on the first day of the month and includes all payments due that month,
        # so the payment can already be exported while the shares are not valid yet
        # and the member can still cancel during the trial period.
        member = MemberFactory.create()
        cancelled_transaction = CoopShareTransactionFactory.create(
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.datetime(year=2024, month=9, day=28),
        )
        exported_payment = PaymentFactory.create(
            mandate_ref__member=member,
            coop_share_transaction=cancelled_transaction,
            status=Payment.PaymentStatus.PAID,
        )

        CoopMembershipCancellationManager.cancel_coop_membership(member)

        exported_payment.refresh_from_db()
        self.assertIsNone(exported_payment.coop_share_transaction)
        self.assertEqual(Payment.PaymentStatus.PAID, exported_payment.status)
