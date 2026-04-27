from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.views.member.list.modals import save_member_and_assign_number


class TestSaveMemberAndAssignNumber(SimpleTestCase):
    @patch.object(
        MemberNumberService,
        "assign_member_number_if_eligible",
        autospec=True,
        return_value=True,
    )
    def test_saveMemberAndAssignNumber_eligible_savesMemberAndDelegatesToService(
        self, mock_assign_if_eligible
    ):
        member = Mock()

        save_member_and_assign_number(member)

        member.save.assert_called_once_with()
        mock_assign_if_eligible.assert_called_once_with(member, cache={})

    @patch.object(
        MemberNumberService,
        "assign_member_number_if_eligible",
        autospec=True,
        return_value=False,
    )
    def test_saveMemberAndAssignNumber_notEligible_savesMemberTwice(
        self, mock_assign_if_eligible
    ):
        member = Mock()

        save_member_and_assign_number(member)

        self.assertEqual(2, member.save.call_count)
        mock_assign_if_eligible.assert_called_once_with(member, cache={})
