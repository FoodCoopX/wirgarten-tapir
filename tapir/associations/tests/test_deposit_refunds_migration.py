import datetime

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestDepositRefundsMigration(MigratorTestCase):
    migrate_from = (
        "associations",
        "0017_associationdepositmembershipchangedlogentry_and_more",
    )
    migrate_to = (
        "associations",
        "0018_associationdepositrefundcreatedlogentry_and_more",
    )

    def prepare(self):
        Member = self.old_state.apps.get_model("wirgarten", "Member")
        Account = self.old_state.apps.get_model(
            "associations", "AssociationDepositAccount"
        )
        Receipt = self.old_state.apps.get_model(
            "associations", "AssociationDepositReceipt"
        )
        File = self.old_state.apps.get_model("wirgarten", "ExportedFile")
        Transaction = self.old_state.apps.get_model("wirgarten", "PaymentTransaction")
        Mandate = self.old_state.apps.get_model("wirgarten", "MandateReference")
        Payment = self.old_state.apps.get_model("wirgarten", "Payment")
        member = Member.objects.create(
            username="refund-history", email="refund-history@example.test"
        )
        account = Account.objects.create(
            member=member,
            agreed_amount=200,
            effective_from=datetime.date(2026, 11, 6),
            instalment_count=4,
            agreement_revision=7,
        )
        Receipt.objects.create(
            account=account,
            amount=25,
            received_on=datetime.date(2026, 11, 6),
            reference="historic-cash",
            note="Beleg",
        )
        csv = File.objects.create(
            name="Historische Bankdatei", type="csv", file=b"historical csv"
        )
        xml = File.objects.create(
            name="Historische Bankdatei", type="xml", file=b"historical xml"
        )
        transaction = Transaction.objects.create(
            csv_file=csv,
            xml_file=xml,
            type="Vereinseinlage",
            month=datetime.date(2026, 11, 1),
        )
        mandate = Mandate.objects.create(
            member=member,
            ref="HISTORIC-REFUND",
            start_ts=datetime.datetime(2026, 11, 6, tzinfo=datetime.timezone.utc),
        )
        Payment.objects.create(
            association_deposit_account=account,
            mandate_ref=mandate,
            amount=50,
            due_date=datetime.date(2026, 11, 6),
            status="PAID",
            transaction=transaction,
            type="Vereinseinlage",
        )
        self.before = {
            name: list(
                self.old_state.apps.get_model(app, name).objects.order_by("pk").values()
            )
            for app, name in [
                ("associations", "AssociationDepositAccount"),
                ("associations", "AssociationDepositReceipt"),
                ("wirgarten", "Payment"),
                ("wirgarten", "PaymentTransaction"),
                ("wirgarten", "ExportedFile"),
            ]
        }

    def test_additive_refund_models_preserve_accounts_receipts_and_exported_history(
        self,
    ):
        for app, name in [
            ("associations", "AssociationDepositAccount"),
            ("associations", "AssociationDepositReceipt"),
            ("wirgarten", "Payment"),
            ("wirgarten", "PaymentTransaction"),
            ("wirgarten", "ExportedFile"),
        ]:
            with self.subTest(model=name):
                after = list(
                    self.new_state.apps.get_model(app, name)
                    .objects.order_by("pk")
                    .values()
                )
                if name == "AssociationDepositAccount":
                    for row in after:
                        self.assertFalse(row.pop("refund_requires_agreement"))
                self.assertEqual(self.before[name], after)
        Refund = self.new_state.apps.get_model(
            "associations", "AssociationDepositRefund"
        )
        self.assertFalse(Refund.objects.exists())
