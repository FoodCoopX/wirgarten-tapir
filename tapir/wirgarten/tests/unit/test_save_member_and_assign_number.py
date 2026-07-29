from unittest.mock import Mock, patch

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.tests.test_utils import TapirUnitTest
from tapir.wirgarten.views.member.list.modals import save_member_and_assign_number


class TestSaveMemberAndAssignNumber(TapirUnitTest):
    @patch.object(
        MemberNumberService,
        "assign_member_number_if_eligible",
        autospec=True,
        return_value=True,
    )
    def test_saveMemberAndAssignNumber_eligible_savesMemberAndDelegatesToService(
        self, mock_assign_if_eligible: Mock
    ):
        form = Mock()
        logged_in_user = Mock()
        form.request.user = logged_in_user
        member = Mock()
        form.instance = member

        save_member_and_assign_number(form)

        form.save.assert_called_once_with()
        mock_assign_if_eligible.assert_called_once_with(
            member, cache={}, actor=logged_in_user
        )
        member.save.assert_not_called()

    @patch.object(
        MemberNumberService,
        "assign_member_number_if_eligible",
        autospec=True,
        return_value=False,
    )
    def test_saveMemberAndAssignNumber_notEligible_savesMemberTwice(
        self, mock_assign_if_eligible: Mock
    ):
        form = Mock()
        logged_in_user = Mock()
        form.request.user = logged_in_user
        member = Mock()
        form.instance = member

        save_member_and_assign_number(form)

        form.save.assert_called_once_with()
        member.save.assert_called_once_with()
        mock_assign_if_eligible.assert_called_once_with(
            member, cache={}, actor=logged_in_user
        )
