import datetime

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestDepositOpeningImportMigration(MigratorTestCase):
    migrate_from = (
        "associations",
        "0018_associationdepositrefundcreatedlogentry_and_more",
    )
    migrate_to = ("associations", "0019_deposit_opening_import")

    def prepare(self):
        Member = self.old_state.apps.get_model("wirgarten", "Member")
        Account = self.old_state.apps.get_model(
            "associations", "AssociationDepositAccount"
        )
        Receipt = self.old_state.apps.get_model(
            "associations", "AssociationDepositReceipt"
        )
        Refund = self.old_state.apps.get_model(
            "associations", "AssociationDepositRefund"
        )
        member = Member.objects.create(
            username="import-history", email="import-history@example.test"
        )
        account = Account.objects.create(
            member=member,
            agreed_amount=100,
            effective_from=datetime.date(2026, 1, 1),
            agreement_revision=7,
            refund_requires_agreement=True,
            collection_stopped_from=datetime.date(2026, 10, 1),
        )
        Receipt.objects.create(
            account=account,
            amount=25,
            received_on=datetime.date(2026, 1, 1),
            reference="history",
            note="Beleg",
        )
        Refund.objects.create(
            account=account,
            amount=10,
            refunded_on=datetime.date(2026, 2, 1),
            reference="return-history",
            note="Bankbeleg",
        )
        self.before = {
            name: list(
                self.old_state.apps.get_model("associations", name).objects.values()
            )
            for name in [
                "AssociationDepositAccount",
                "AssociationDepositReceipt",
                "AssociationDepositRefund",
            ]
        }

    def test_additive_import_audit_preserves_existing_balances_holds_and_history(self):
        for name, rows in self.before.items():
            with self.subTest(model=name):
                self.assertEqual(
                    rows,
                    list(
                        self.new_state.apps.get_model(
                            "associations", name
                        ).objects.values()
                    ),
                )
        Audit = self.new_state.apps.get_model(
            "associations", "AssociationDepositImportedLogEntry"
        )
        self.assertFalse(Audit.objects.exists())
