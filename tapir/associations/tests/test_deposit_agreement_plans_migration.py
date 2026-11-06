import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestDepositAgreementPlansMigration(MigratorTestCase):
    migrate_from = ("associations", "0014_deposit_increases")
    migrate_to = ("associations", "0016_deposit_individual_agreement")

    def prepare(self):
        Member = self.old_state.apps.get_model("wirgarten", "Member")
        Account = self.old_state.apps.get_model(
            "associations", "AssociationDepositAccount"
        )
        for index, amount in enumerate([None, Decimal("0"), Decimal("200")]):
            member = Member.objects.create(
                username=f"existing-{index}", email=f"existing-{index}@example.test"
            )
            Account.objects.create(
                member=member,
                agreed_amount=amount,
                effective_from=(
                    datetime.date(2026, 1, 1) if amount is not None else None
                ),
            )
        self.before = list(Account.objects.order_by("pk").values())

    def test_existing_agreements_are_preserved_without_requests_or_new_assessments(
        self,
    ):
        Account = self.new_state.apps.get_model(
            "associations", "AssociationDepositAccount"
        )
        after = list(Account.objects.order_by("pk").values())
        for row in after:
            self.assertIsNone(row.pop("hardship_requested_at"))
            self.assertEqual(0, row.pop("agreement_revision"))
            self.assertEqual(1, row.pop("instalment_count"))
            self.assertFalse(row.pop("is_individual_agreement"))
        self.assertEqual(self.before, after)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Account.objects.filter(pk=after[0]["id"]).update(instalment_count=0)
