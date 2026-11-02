import datetime
from decimal import Decimal

from django_test_migrations.contrib.unittest_case import MigratorTestCase

MIGRATION_BEFORE = ("wirgarten", "0139_payment_coop_share_transaction")
MIGRATION_TESTED = ("wirgarten", "0140_link_payments_to_coop_share_transactions")


# Each test class migrates the whole project from scratch, which takes several seconds.
# The scenarios are therefore grouped so that each migration direction runs only once.
class LinkPaymentsMigratorTestCase(MigratorTestCase):
    migrate_from = MIGRATION_BEFORE
    migrate_to = MIGRATION_TESTED

    def _create_mandate_ref(self, member_no: int):
        member = self.old_state.apps.get_model("wirgarten", "Member").objects.create(
            username=f"test_member_{member_no}",
            email=f"test_{member_no}@example.com",
            member_no=member_no,
        )
        return self.old_state.apps.get_model(
            "wirgarten", "MandateReference"
        ).objects.create(
            ref=f"TEST/REF/{member_no}",
            member=member,
            start_ts=datetime.datetime(year=2025, month=1, day=1, tzinfo=datetime.UTC),
        )

    def _create_payment(self, mandate_ref, amount, exported: bool):
        payment_transaction_id = None
        if exported:
            payment_transaction_id = (
                self.old_state.apps.get_model("wirgarten", "PaymentTransaction")
                .objects.create(
                    csv_file=self.old_state.apps.get_model(
                        "wirgarten", "ExportedFile"
                    ).objects.create(name="export.csv", type="csv", file=b""),
                    type="Genossenschaftsanteile",
                    month=datetime.date(year=2025, month=6, day=1),
                )
                .id
            )
        return self.old_state.apps.get_model("wirgarten", "Payment").objects.create(
            due_date=datetime.date(year=2025, month=6, day=15),
            mandate_ref_id=mandate_ref.ref,
            amount=Decimal(amount),
            status="PAID" if exported else "DUE",
            transaction_id=payment_transaction_id,
            type="Genossenschaftsanteile",
        )

    def _create_transaction(self, mandate_ref, payment, quantity: int, day: int):
        return self.old_state.apps.get_model(
            "wirgarten", "CoopShareTransaction"
        ).objects.create(
            transaction_type="purchase",
            member_id=mandate_ref.member_id,
            quantity=quantity,
            share_price=Decimal(50),
            timestamp=datetime.datetime(
                year=2025, month=5, day=day, tzinfo=datetime.UTC
            ),
            valid_at=datetime.date(year=2025, month=6, day=1),
            mandate_ref_id=mandate_ref.ref,
            payment=payment,
        )

    def _get_payments_by_transaction_id(self):
        return {
            payment.coop_share_transaction_id: payment
            for payment in self.new_state.apps.get_model(
                "wirgarten", "Payment"
            ).objects.all()
        }
