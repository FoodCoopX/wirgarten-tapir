import datetime

from tapir.associations.models import AssociationDepositTransaction
from tapir.associations.services.association_deposit_annotator import (
    AssociationDepositAnnotator,
)
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAssociationDepositAnnotator(TapirIntegrationTest):
    def test_annotateMembers_receivedAndOutstandingTransactions_distinguishesBalances(
        self,
    ):
        member = MemberFactory.create()
        for kind, amount in (
            (AssociationDepositTransaction.Type.IMPORT, 100),
            (AssociationDepositTransaction.Type.IMPORT_OUTSTANDING, 50),
        ):
            AssociationDepositTransaction.objects.create(
                member=member,
                transaction_type=kind,
                amount=amount,
                valid_at=datetime.date(2026, 11, 5),
            )
        paid = AssociationDepositTransaction.objects.create(
            member=member,
            transaction_type=AssociationDepositTransaction.Type.SUBSCRIPTION,
            amount=200,
            valid_at=datetime.date(2026, 11, 5),
        )
        PaymentFactory.create(
            association_deposit_transaction=paid,
            mandate_ref__member=member,
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
            amount=200,
        )
        pending = AssociationDepositTransaction.objects.create(
            member=member,
            transaction_type=AssociationDepositTransaction.Type.SUBSCRIPTION,
            amount=25,
            valid_at=datetime.date(2026, 11, 5),
        )
        PaymentFactory.create(
            association_deposit_transaction=pending,
            mandate_ref__member=member,
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
            amount=25,
            transaction=None,
        )
        AssociationDepositTransaction.objects.create(
            member=MemberFactory.create(),
            transaction_type=AssociationDepositTransaction.Type.IMPORT,
            amount=500,
            valid_at=datetime.date(2026, 11, 5),
        )

        result = AssociationDepositAnnotator.annotate_members(
            Member.objects.filter(pk=member.pk)
        ).get()

        self.assertEqual(375, result.deposit_agreed)
        self.assertEqual(300, result.deposit_exported)
