import datetime

from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, CoopShareTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCancelCoopMembership(TapirIntegrationTest):
    def setUp(self) -> None:
        mock_timezone(self, datetime.datetime(year=2024, month=9, day=27))
        ParameterDefinitions().import_definitions()

    def test_cancelCoopMembership_default_deletesAllFutureSharePurchases(self):
        member = MemberFactory.create()

        transaction_1 = CoopShareTransactionFactory.create(  # transaction in the past, should not be deleted
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.datetime(year=2024, month=9, day=26),
        )
        transaction_2 = CoopShareTransactionFactory.create(  # is not a purchase, should not be deleted
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
            valid_at=datetime.datetime(year=2024, month=9, day=28),
            quantity=-1,
        )
        CoopShareTransactionFactory.create(  # should get deleted
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.datetime(year=2024, month=9, day=28),
        )

        MembershipCancellationManager.cancel_coop_membership(member)

        self.assertEqual(2, CoopShareTransaction.objects.count())
        self.assertIn(transaction_1, CoopShareTransaction.objects.all())
        self.assertIn(transaction_2, CoopShareTransaction.objects.all())
