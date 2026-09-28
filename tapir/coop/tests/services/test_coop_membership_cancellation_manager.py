import datetime
from unittest.mock import patch, MagicMock

from tapir.coop.services.coop_membership_cancellation_manager import (
    CoopMembershipCancellationManager,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestCoopMembershipCancellationManager(TapirUnitTest):
    @patch.object(
        CoopMembershipCancellationManager, "get_coop_entry_date", autospec=True
    )
    def test_isInCoopTrial_noEntryDate_returnsFalse(
        self, mock_get_coop_entry_date: MagicMock
    ):
        mock_get_coop_entry_date.return_value = None
        member = MagicMock()
        reference_date = MagicMock()
        cache = MagicMock()

        result = CoopMembershipCancellationManager.is_in_coop_trial(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)
        mock_get_coop_entry_date.assert_called_once_with(member, cache)

    @patch.object(
        CoopMembershipCancellationManager, "get_coop_entry_date", autospec=True
    )
    def test_isInCoopTrial_entryDateIsBeforeReferenceDate_returnsFalse(
        self, mock_get_coop_entry_date: MagicMock
    ):
        mock_get_coop_entry_date.return_value = datetime.date(
            year=2025, month=3, day=10
        )
        member = MagicMock()
        reference_date = datetime.date(year=2025, month=3, day=11)
        cache = MagicMock()

        result = CoopMembershipCancellationManager.is_in_coop_trial(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)
        mock_get_coop_entry_date.assert_called_once_with(member, cache)

    @patch.object(
        CoopMembershipCancellationManager, "get_coop_entry_date", autospec=True
    )
    def test_isInCoopTrial_entryDateIsAfterReferenceDate_returnsTrue(
        self, mock_get_coop_entry_date: MagicMock
    ):
        mock_get_coop_entry_date.return_value = datetime.date(
            year=2025, month=3, day=10
        )
        member = MagicMock()
        reference_date = datetime.date(year=2025, month=3, day=9)
        cache = MagicMock()

        result = CoopMembershipCancellationManager.is_in_coop_trial(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertTrue(result)
        mock_get_coop_entry_date.assert_called_once_with(member, cache)

    @patch.object(
        CoopMembershipCancellationManager, "get_coop_entry_date", autospec=True
    )
    def test_isInCoopTrial_entryDateIsSameAsReferenceDate_returnsFalse(
        self, mock_get_coop_entry_date: MagicMock
    ):
        mock_get_coop_entry_date.return_value = datetime.date(
            year=2025, month=3, day=10
        )
        member = MagicMock()
        reference_date = datetime.date(year=2025, month=3, day=10)
        cache = MagicMock()

        result = CoopMembershipCancellationManager.is_in_coop_trial(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)
        mock_get_coop_entry_date.assert_called_once_with(member, cache)
