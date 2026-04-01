import datetime
from decimal import Decimal

from tapir.coop.models import CoopSharesCancelledLogEntry
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
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

        MembershipCancellationManager.cancel_coop_membership(member=member, actor=actor)

        self.assertEqual(2, CoopShareTransaction.objects.count())
        self.assertIn(transaction_1, CoopShareTransaction.objects.all())
        self.assertIn(transaction_2, CoopShareTransaction.objects.all())

        self.assertEqual(1, CoopSharesCancelledLogEntry.objects.count())
        log_entry = CoopSharesCancelledLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)
        self.assertEqual(transaction_3.quantity, log_entry.nb_shares)
        self.assertEqual(transaction_3.valid_at, log_entry.shares_valid_at)

    def test_cancelCoopMembership_default_paymentsGetUpdateCorrectly(
        self,
    ):
        member = MemberFactory.create()

        payment_1 = PaymentFactory.create(
            mandate_ref__member=member, amount=Decimal(100)
        )
        CoopShareTransactionFactory.create(
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.datetime(year=2024, month=9, day=28),
            payment=payment_1,
            share_price=Decimal(100),
            quantity=1,
        )

        payment_2 = PaymentFactory.create(
            mandate_ref__member=member, amount=Decimal(350)
        )
        CoopShareTransactionFactory.create(
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.datetime(year=2024, month=9, day=28),
            payment=payment_2,
            share_price=Decimal(100),
            quantity=2,
        )

        MembershipCancellationManager.cancel_coop_membership(member)

        self.assertFalse(CoopShareTransaction.objects.exists())
        self.assertEqual(1, Payment.objects.count(), "payment_1 should be deleted")
        payment_2.refresh_from_db()
        self.assertEqual(
            Decimal(150),
            payment_2.amount,
            "Payment 2 should have been reduced by the total cost of transaction_2",
        )
