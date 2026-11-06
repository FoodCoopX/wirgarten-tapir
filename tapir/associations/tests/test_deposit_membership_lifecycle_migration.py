import datetime
from decimal import Decimal

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestDepositMembershipLifecycleMigration(MigratorTestCase):
    migrate_from = ("associations", "0016_deposit_individual_agreement")
    migrate_to = (
        "associations",
        "0017_associationdepositmembershipchangedlogentry_and_more",
    )

    def prepare(self):
        Member = self.old_state.apps.get_model("wirgarten", "Member")
        Account = self.old_state.apps.get_model(
            "associations", "AssociationDepositAccount"
        )
        Receipt = self.old_state.apps.get_model(
            "associations", "AssociationDepositReceipt"
        )
        for index, amount in enumerate([None, Decimal("0"), Decimal("100")]):
            member = Member.objects.create(
                username=f"lifecycle-{index}", email=f"lifecycle-{index}@example.test"
            )
            account = Account.objects.create(
                member=member,
                agreed_amount=amount,
                effective_from=(
                    datetime.date(2026, 11, 5) if amount is not None else None
                ),
                instalment_count=4,
                agreement_revision=3,
            )
            Receipt.objects.create(
                account=account,
                amount=25,
                received_on=datetime.date(2026, 11, 5),
                reference=f"historic-{index}",
                note="Beleg",
            )
        self.accounts = list(Account.objects.order_by("pk").values())
        self.receipts = list(Receipt.objects.order_by("pk").values())

    def test_additive_default_preserves_accounts_and_receipts(self):
        Account = self.new_state.apps.get_model(
            "associations", "AssociationDepositAccount"
        )
        Receipt = self.new_state.apps.get_model(
            "associations", "AssociationDepositReceipt"
        )
        after = list(Account.objects.order_by("pk").values())
        for account in after:
            self.assertIsNone(account.pop("collection_stopped_from"))
        self.assertEqual(self.accounts, after)
        self.assertEqual(self.receipts, list(Receipt.objects.order_by("pk").values()))
