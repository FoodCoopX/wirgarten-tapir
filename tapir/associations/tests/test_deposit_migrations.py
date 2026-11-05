import datetime
from decimal import Decimal

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestDepositMigrationPreservesExistingPayments(MigratorTestCase):
    migrate_from = ("wirgarten", "0145_waitinglistentry_replace_zero_phone_number")
    migrate_to = ("wirgarten", "0146_payment_association_deposit")

    def prepare(self):
        apps = self.old_state.apps
        member = apps.get_model("wirgarten", "Member").objects.create(
            username="existing-member", email="member@example.com", member_no=42
        )
        mandate = apps.get_model("wirgarten", "MandateReference").objects.create(
            member=member,
            ref="TEST/42",
            start_ts=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
        )
        file = apps.get_model("wirgarten", "ExportedFile").objects.create(
            name="existing.csv", type="csv", file=b"existing financial history"
        )
        transaction = apps.get_model("wirgarten", "PaymentTransaction").objects.create(
            csv_file=file, type="Vereinsmitgliedschaft", month=datetime.date(2025, 1, 1)
        )
        self.payment_id = (
            apps.get_model("wirgarten", "Payment")
            .objects.create(
                mandate_ref=mandate,
                amount=Decimal("12.50"),
                type="Vereinsmitgliedschaft",
                status="PAID",
                transaction=transaction,
                due_date=datetime.date(2025, 1, 15),
            )
            .pk
        )
        self.transaction_id = transaction.pk

    def test_existing_fees_remain_fees_and_no_deposit_or_debit_is_created(self):
        apps = self.new_state.apps
        payments = apps.get_model("wirgarten", "Payment").objects.all()
        self.assertEqual(1, payments.count())
        payment = payments.get(pk=self.payment_id)
        self.assertEqual(Decimal("12.50"), payment.amount)
        self.assertEqual("PAID", payment.status)
        self.assertEqual("Vereinsmitgliedschaft", payment.type)
        self.assertIsNone(payment.association_deposit_id)
        self.assertEqual(self.transaction_id, payment.transaction_id)
        self.assertEqual(
            b"existing financial history", bytes(payment.transaction.csv_file.file)
        )
        self.assertFalse(
            apps.get_model("associations", "AssociationDeposit").objects.exists()
        )
