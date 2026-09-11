from unittest.mock import patch, Mock, call

from tapir.associations.services.association_membership_cancellation_manager import (
    AssociationMembershipCancellationManager,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestDoesMemberHaveACancellableMembership(TapirUnitTest):
    @patch.object(
        AssociationMembershipCancellationManager,
        "_can_membership_be_cancelled",
        autospec=True,
    )
    @patch.object(TapirCache, "get_member_association_memberships", autospec=True)
    def test_doesMemberHaveACancellableMembership_noMembership_returnsFalse(
        self,
        mock_get_member_association_memberships: Mock,
        mock_can_membership_be_cancelled: Mock,
    ):
        mock_get_member_association_memberships.return_value = []
        member = Mock()
        reference_date = Mock()
        cache = Mock()

        self.assertFalse(
            AssociationMembershipCancellationManager.does_member_have_a_cancellable_membership(
                member=member, reference_date=reference_date, cache=cache
            )
        )

        mock_get_member_association_memberships.assert_called_once_with(
            member=member, cache=cache
        )
        mock_can_membership_be_cancelled.assert_not_called()

    @patch.object(
        AssociationMembershipCancellationManager,
        "_can_membership_be_cancelled",
        autospec=True,
    )
    @patch.object(TapirCache, "get_member_association_memberships", autospec=True)
    def test_doesMemberHaveACancellableMembership_noCancellableMembership_returnsFalse(
        self,
        mock_get_member_association_memberships: Mock,
        mock_can_membership_be_cancelled: Mock,
    ):
        memberships = AssociationMembershipFactory.build_batch(
            size=3, cancellation_ts=Mock()
        )
        mock_get_member_association_memberships.return_value = memberships
        mock_can_membership_be_cancelled.return_value = False
        member = Mock()
        reference_date = Mock()
        cache = Mock()

        self.assertFalse(
            AssociationMembershipCancellationManager.does_member_have_a_cancellable_membership(
                member=member, reference_date=reference_date, cache=cache
            )
        )

        mock_get_member_association_memberships.assert_called_once_with(
            member=member, cache=cache
        )
        self.assertEqual(3, mock_can_membership_be_cancelled.call_count)
        mock_can_membership_be_cancelled.assert_has_calls(
            [
                call(membership=membership, reference_date=reference_date)
                for membership in memberships
            ],
            any_order=True,
        )

    @patch.object(
        AssociationMembershipCancellationManager,
        "_can_membership_be_cancelled",
        autospec=True,
    )
    @patch.object(TapirCache, "get_member_association_memberships", autospec=True)
    def test_doesMemberHaveACancellableMembership_oneCancellableMembership_returnsTrue(
        self,
        mock_get_member_association_memberships: Mock,
        mock_can_membership_be_cancelled: Mock,
    ):
        memberships = AssociationMembershipFactory.build_batch(
            size=20, cancellation_ts=Mock()
        )
        mock_get_member_association_memberships.return_value = memberships
        mock_can_membership_be_cancelled.side_effect = (
            lambda membership, **kwargs: membership == memberships[3]
        )
        member = Mock()
        reference_date = Mock()
        cache = Mock()

        self.assertTrue(
            AssociationMembershipCancellationManager.does_member_have_a_cancellable_membership(
                member=member, reference_date=reference_date, cache=cache
            )
        )

        mock_get_member_association_memberships.assert_called_once_with(
            member=member, cache=cache
        )
        self.assertEqual(4, mock_can_membership_be_cancelled.call_count)
        mock_can_membership_be_cancelled.assert_has_calls(
            [
                call(membership=membership, reference_date=reference_date)
                for membership in memberships[:4]
            ],
            any_order=True,
        )
