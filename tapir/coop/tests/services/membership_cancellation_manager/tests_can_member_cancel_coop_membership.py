import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestCanMemberCancelCoopMembership(SimpleTestCase):
    def setUp(self):
        mock_timezone(self, datetime.datetime(year=2024, month=1, day=15))

    @patch.object(MembershipCancellationManager, "get_coop_entry_date")
    def test_canMemberCancelCoopMembership_noEntryDate_returnsFalse(
        self, mock_get_coop_entry_date: Mock
    ):
        mock_get_coop_entry_date.return_value = None
        member = Mock()

        result = MembershipCancellationManager.can_member_cancel_coop_membership(member)

        self.assertFalse(result)
        mock_get_coop_entry_date.assert_called_once_with(member)

    @patch.object(MembershipCancellationManager, "get_coop_entry_date")
    def test_canMemberCancelCoopMembership_entryDateIsInThePast_returnsFalse(
        self, mock_get_coop_entry_date: Mock
    ):
        mock_get_coop_entry_date.return_value = datetime.date(
            year=2024, month=1, day=14
        )
        member = Mock()

        result = MembershipCancellationManager.can_member_cancel_coop_membership(member)

        self.assertFalse(result)
        mock_get_coop_entry_date.assert_called_once_with(member)

    @patch.object(MembershipCancellationManager, "get_coop_entry_date")
    def test_canMemberCancelCoopMembership_entryDateIsInTheFuture_returnsTrue(
        self, mock_get_coop_entry_date: Mock
    ):
        mock_get_coop_entry_date.return_value = datetime.date(
            year=2024, month=1, day=16
        )
        member = Mock()

        result = MembershipCancellationManager.can_member_cancel_coop_membership(member)

        self.assertTrue(result)
        mock_get_coop_entry_date.assert_called_once_with(member)
