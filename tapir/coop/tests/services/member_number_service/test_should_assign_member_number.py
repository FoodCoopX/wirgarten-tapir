from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestShouldAssignMemberNumber(TapirUnitTest):
    def test_shouldAssignMemberNumber_memberAlreadyHasNumber_returnsFalse(self):
        member = MemberFactory.build(member_no=5)

        self.assertFalse(MemberNumberService.should_assign_member_number(member))

    def test_shouldAssignMemberNumber_memberDoesntHaveNumber_returnsTrue(self):
        member = MemberFactory.build()
        member.member_no = None

        self.assertTrue(MemberNumberService.should_assign_member_number(member))
