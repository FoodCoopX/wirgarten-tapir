import datetime

from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, CoopShareTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetCoopEntryDate(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

    def test_getCoopEntryDate_memberHasNoShares_returnsNone(self):
        member = MemberFactory.create()

        result = MembershipCancellationManager.get_coop_entry_date(member)

        self.assertIsNone(result)

    def test_getCoopEntryDate_memberHasShares_returnsEarliestShareDate(self):
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.date(year=2024, month=12, day=6),
        )
        CoopShareTransactionFactory.create(
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=datetime.date(year=2024, month=12, day=8),
        )
        CoopShareTransactionFactory.create(
            member=member,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
            valid_at=datetime.date(year=2024, month=12, day=5),
            quantity=-1,
        )

        result = MembershipCancellationManager.get_coop_entry_date(member)

        self.assertEqual(datetime.date(year=2024, month=12, day=6), result)
