import datetime
from decimal import Decimal

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestDepositReceiptsMigration(MigratorTestCase):
    migrate_from = ("wirgarten", "0145_waitinglistentry_replace_zero_phone_number")
    migrate_to = ("associations", "0011_deposit_receipts")

    def prepare(self):
        member = self.old_state.apps.get_model("wirgarten", "Member").objects.create(
            username="existing-member", email="existing@example.test", member_no=123
        )
        mandate = self.old_state.apps.get_model(
            "wirgarten", "MandateReference"
        ).objects.create(
            ref="existing-mandate",
            member=member,
            start_ts=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
        )
        self.member_id = member.pk
        payment_model = self.old_state.apps.get_model("wirgarten", "Payment")
        for status in ["PAID", "DUE"]:
            payment_model.objects.create(
                mandate_ref=mandate,
                amount=Decimal("25.00"),
                status=status,
                due_date=datetime.date(2026, 11, 5),
                type="Vereinsbeitrag",
            )
        self.payments = list(payment_model.objects.order_by("pk").values())

    def test_existing_members_and_payments_are_preserved_without_backfill(self):
        member = self.new_state.apps.get_model("wirgarten", "Member").objects.get(
            pk=self.member_id
        )
        self.assertEqual(123, member.member_no)
        self.assertEqual("existing@example.test", member.email)
        self.assertEqual(
            self.payments,
            list(
                self.new_state.apps.get_model("wirgarten", "Payment")
                .objects.order_by("pk")
                .values()
            ),
        )
        for name in [
            "AssociationDepositAccount",
            "AssociationDepositReceipt",
            "AssociationDepositReceiptCreatedLogEntry",
        ]:
            with self.subTest(model=name):
                self.assertFalse(
                    self.new_state.apps.get_model("associations", name).objects.exists()
                )
