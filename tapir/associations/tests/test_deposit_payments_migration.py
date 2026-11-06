import datetime
from decimal import Decimal

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestDepositPaymentsMigration(MigratorTestCase):
    migrate_from = ("wirgarten", "0145_waitinglistentry_replace_zero_phone_number")
    migrate_to = ("wirgarten", "0146_deposit_payments")

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
        payment_model = self.old_state.apps.get_model("wirgarten", "Payment")
        for kind, status in [
            ("Genossenschaftsanteile", "PAID"),
            ("Vereinsbeitrag", "DUE"),
        ]:
            payment_model.objects.create(
                mandate_ref=mandate,
                amount=Decimal("25.00"),
                status=status,
                due_date=datetime.date(2026, 11, 5),
                type=kind,
            )
        self.payments = list(payment_model.objects.order_by("pk").values())

    def test_existing_payments_keep_their_fields_without_deposit_assignment(self):
        payments = list(
            self.new_state.apps.get_model("wirgarten", "Payment")
            .objects.order_by("pk")
            .values()
        )
        for payment in payments:
            self.assertIsNone(payment.pop("association_deposit_account_id"))
        self.assertEqual(self.payments, payments)
        self.assertFalse(
            self.new_state.apps.get_model(
                "associations", "AssociationDepositAccount"
            ).objects.exists()
        )
