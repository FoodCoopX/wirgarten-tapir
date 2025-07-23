from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import (
    ParameterDefinitions,
)
from tapir.wirgarten.service.member import transfer_coop_shares
from tapir.wirgarten.tests.factories import MemberFactory, MemberWithCoopSharesFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_today


class TestTransferCoopShares(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_transferCoopShares_default_newMembersEntryDateIsTransferDate(self):
        receiving_member: Member = MemberFactory.create()
        giving_member: Member = MemberWithCoopSharesFactory.create(
            add_coop_shares__quantity=4
        )

        self.assertEqual(0, receiving_member.coop_shares_quantity)
        self.assertEqual(4, giving_member.coop_shares_quantity)

        transfer_coop_shares(
            origin_member_id=giving_member.id,
            target_member_id=receiving_member.id,
            quantity=4,
            actor=None,
        )

        self.assertEqual(4, receiving_member.coop_shares_quantity)
        self.assertEqual(0, giving_member.coop_shares_quantity)
        self.assertEqual(
            get_today(),
            MembershipCancellationManager.get_coop_entry_date(receiving_member),
        )
