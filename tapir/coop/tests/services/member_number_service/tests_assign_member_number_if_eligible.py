from unittest.mock import Mock, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.coop.services.member_number_service import MemberNumberService


class TestAssignMemberNumberIfEligible(TapirUnitTest):
    @patch.object(
        MemberNumberService,
        "compute_next_member_number",
        autospec=True,
        return_value=42,
    )
    @patch.object(
        MemberNumberService,
        "should_assign_member_number",
        autospec=True,
        return_value=True,
    )
    def test_assignMemberNumberIfEligible_eligible_assignsNumberSavesAndReturnsTrue(
        self, mock_should_assign, mock_compute_next
    ):
        member = Mock()
        cache = {}

        result = MemberNumberService.assign_member_number_if_eligible(
            member, cache=cache
        )

        self.assertTrue(result)
        self.assertEqual(42, member.member_no)
        member.save.assert_called_once_with()
        mock_should_assign.assert_called_once_with(member, cache=cache)
        mock_compute_next.assert_called_once_with(cache=cache)

    @patch.object(
        MemberNumberService,
        "compute_next_member_number",
        autospec=True,
    )
    @patch.object(
        MemberNumberService,
        "should_assign_member_number",
        autospec=True,
        return_value=False,
    )
    def test_assignMemberNumberIfEligible_notEligible_doesNothingAndReturnsFalse(
        self, mock_should_assign, mock_compute_next
    ):
        member = Mock()
        cache = {}

        result = MemberNumberService.assign_member_number_if_eligible(
            member, cache=cache
        )

        self.assertFalse(result)
        member.save.assert_not_called()
        mock_compute_next.assert_not_called()
        mock_should_assign.assert_called_once_with(member, cache=cache)
