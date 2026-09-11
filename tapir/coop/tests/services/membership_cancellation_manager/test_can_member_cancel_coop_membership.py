import datetime
from unittest.mock import patch, Mock

from tapir.coop.services.coop_membership_cancellation_manager import (
    CoopMembershipCancellationManager,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestCanMemberCancelCoopMembership(TapirUnitTest):
    def setUp(self):
        self.now = mock_timezone(self, datetime.datetime(year=2024, month=1, day=15))

    @patch.object(CoopMembershipCancellationManager, "get_coop_entry_date")
    def test_canMemberCancelCoopMembership_noEntryDate_returnsFalse(
        self, mock_get_coop_entry_date: Mock
    ):
        mock_get_coop_entry_date.return_value = None
        member = Mock()
        cache = Mock()

        result = CoopMembershipCancellationManager.can_member_cancel_coop_membership(
            member=member, reference_date=self.now.date(), cache=cache
        )

        self.assertFalse(result)
        mock_get_coop_entry_date.assert_called_once_with(member, cache=cache)

    @patch.object(CoopMembershipCancellationManager, "get_coop_entry_date")
    def test_canMemberCancelCoopMembership_entryDateIsInThePast_returnsFalse(
        self, mock_get_coop_entry_date: Mock
    ):
        mock_get_coop_entry_date.return_value = datetime.date(
            year=2024, month=1, day=14
        )
        member = Mock()
        cache = Mock()

        result = CoopMembershipCancellationManager.can_member_cancel_coop_membership(
            member=member, reference_date=self.now.date(), cache=cache
        )

        self.assertFalse(result)
        mock_get_coop_entry_date.assert_called_once_with(member, cache=cache)

    @patch.object(CoopMembershipCancellationManager, "get_coop_entry_date")
    def test_canMemberCancelCoopMembership_entryDateIsInTheFuture_returnsTrue(
        self, mock_get_coop_entry_date: Mock
    ):
        mock_get_coop_entry_date.return_value = datetime.date(
            year=2024, month=1, day=16
        )
        member = Mock()
        cache = Mock()

        result = CoopMembershipCancellationManager.can_member_cancel_coop_membership(
            member=member, reference_date=self.now.date(), cache=cache
        )

        self.assertTrue(result)
        mock_get_coop_entry_date.assert_called_once_with(member, cache=cache)
