import datetime
from decimal import Decimal

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestDepositAgreementsMigration(MigratorTestCase):
    migrate_from = ("associations", "0011_deposit_receipts")
    migrate_to = ("associations", "0012_deposit_agreements")

    def prepare(self):
        member = self.old_state.apps.get_model("wirgarten", "Member").objects.create(
            username="existing-member", email="existing@example.test", member_no=123
        )
        account = self.old_state.apps.get_model(
            "associations", "AssociationDepositAccount"
        ).objects.create(member=member)
        self.account_id = account.pk
        receipt_model = self.old_state.apps.get_model(
            "associations", "AssociationDepositReceipt"
        )
        receipt_model.objects.create(
            account=account,
            reference="historical-25",
            amount=Decimal("25.00"),
            received_on=datetime.date(2026, 11, 1),
            note="Historisch erhalten",
        )
        self.receipts = list(receipt_model.objects.values())

    def test_existing_receipts_keep_unknown_agreement_without_payment(self):
        account = self.new_state.apps.get_model(
            "associations", "AssociationDepositAccount"
        ).objects.get(pk=self.account_id)
        self.assertIsNone(account.agreed_amount)
        self.assertIsNone(account.effective_from)
        self.assertEqual(
            self.receipts,
            list(
                self.new_state.apps.get_model(
                    "associations", "AssociationDepositReceipt"
                ).objects.values()
            ),
        )
        self.assertFalse(
            self.new_state.apps.get_model(
                "associations", "AssociationDepositAgreementCreatedLogEntry"
            ).objects.exists()
        )
        self.assertFalse(
            self.new_state.apps.get_model("wirgarten", "Payment").objects.exists()
        )
