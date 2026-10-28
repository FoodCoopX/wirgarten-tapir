from decimal import Decimal

from tapir.wirgarten.tests.migrations.link_payments_migrator_test_case import (
    LinkPaymentsMigratorTestCase,
)


class TestLinkPaymentsToCoopShareTransactionsForward(LinkPaymentsMigratorTestCase):
    def prepare(self):
        mandate_ref = self._create_mandate_ref(member_no=1)
        self.single_payment = self._create_payment(
            mandate_ref=mandate_ref, amount=100, exported=False
        )
        self.single_transaction = self._create_transaction(
            mandate_ref=mandate_ref, payment=self.single_payment, quantity=2, day=1
        )

        mandate_ref = self._create_mandate_ref(member_no=2)
        self.merged_due_payment = self._create_payment(
            mandate_ref=mandate_ref, amount=250, exported=False
        )
        self.merged_due_first = self._create_transaction(
            mandate_ref=mandate_ref, payment=self.merged_due_payment, quantity=2, day=1
        )
        self.merged_due_second = self._create_transaction(
            mandate_ref=mandate_ref, payment=self.merged_due_payment, quantity=3, day=2
        )

        mandate_ref = self._create_mandate_ref(member_no=3)
        self.merged_exported_payment = self._create_payment(
            mandate_ref=mandate_ref, amount=250, exported=True
        )
        self.merged_exported_first = self._create_transaction(
            mandate_ref=mandate_ref,
            payment=self.merged_exported_payment,
            quantity=2,
            day=1,
        )
        self.merged_exported_second = self._create_transaction(
            mandate_ref=mandate_ref,
            payment=self.merged_exported_payment,
            quantity=3,
            day=2,
        )

        mandate_ref = self._create_mandate_ref(member_no=4)
        self.edited_payment = self._create_payment(
            mandate_ref=mandate_ref, amount=230, exported=False
        )
        self.edited_first = self._create_transaction(
            mandate_ref=mandate_ref, payment=self.edited_payment, quantity=2, day=1
        )
        self.edited_second = self._create_transaction(
            mandate_ref=mandate_ref, payment=self.edited_payment, quantity=3, day=2
        )

    def test_forward(self):
        payments = self._get_payments_by_transaction_id()
        self.assertEqual(7, len(payments))

        with self.subTest("payment for a single transaction gets linked"):
            payment = payments[self.single_transaction.id]
            self.assertEqual(self.single_payment.id, payment.id)
            self.assertEqual(Decimal(100), payment.amount)

        with self.subTest("merged due payment gets split"):
            first = payments[self.merged_due_first.id]
            second = payments[self.merged_due_second.id]
            self.assertEqual(self.merged_due_payment.id, first.id)
            self.assertEqual(Decimal(100), first.amount)
            self.assertEqual(Decimal(150), second.amount)
            self.assertEqual("DUE", second.status)
            self.assertIsNone(second.transaction_id)
            self.assertEqual(self.merged_due_payment.due_date, second.due_date)

        with self.subTest("merged exported payment gets split and keeps the export"):
            for transaction in [
                self.merged_exported_first,
                self.merged_exported_second,
            ]:
                payment = payments[transaction.id]
                self.assertEqual("PAID", payment.status)
                self.assertEqual(
                    self.merged_exported_payment.transaction_id,
                    payment.transaction_id,
                )

        with self.subTest("difference to the expected amount stays on the first"):
            self.assertEqual(Decimal(80), payments[self.edited_first.id].amount)
            self.assertEqual(Decimal(150), payments[self.edited_second.id].amount)
