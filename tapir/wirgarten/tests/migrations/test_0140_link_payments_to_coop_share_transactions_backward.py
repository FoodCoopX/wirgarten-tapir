from decimal import Decimal

from tapir.wirgarten.tests.migrations.link_payments_migrator_test_case import (
    LinkPaymentsMigratorTestCase,
    MIGRATION_BEFORE,
    MIGRATION_TESTED,
)


class TestLinkPaymentsToCoopShareTransactionsBackward(LinkPaymentsMigratorTestCase):
    migrate_from = MIGRATION_TESTED
    migrate_to = MIGRATION_BEFORE

    def prepare(self):
        mandate_ref = self._create_mandate_ref(member_no=1)
        self.first_payment = self._create_payment(
            mandate_ref=mandate_ref, amount=100, exported=False
        )
        self.first = self._create_transaction(
            mandate_ref=mandate_ref, payment=self.first_payment, quantity=2, day=1
        )
        self.first_payment.coop_share_transaction = self.first
        self.first_payment.save()
        second_payment = self._create_payment(
            mandate_ref=mandate_ref, amount=150, exported=False
        )
        self.second = self._create_transaction(
            mandate_ref=mandate_ref, payment=second_payment, quantity=3, day=2
        )
        second_payment.coop_share_transaction = self.second
        second_payment.save()

    def test_backward_splitPayments_mergedAgain(self):
        payment_class = self.new_state.apps.get_model("wirgarten", "Payment")
        transaction_class = self.new_state.apps.get_model(
            "wirgarten", "CoopShareTransaction"
        )

        self.assertEqual(1, payment_class.objects.count())
        merged_payment = payment_class.objects.get()
        self.assertEqual(Decimal(250), merged_payment.amount)
        self.assertEqual(
            merged_payment.id,
            transaction_class.objects.get(id=self.first.id).payment_id,
        )
        self.assertEqual(
            merged_payment.id,
            transaction_class.objects.get(id=self.second.id).payment_id,
        )
