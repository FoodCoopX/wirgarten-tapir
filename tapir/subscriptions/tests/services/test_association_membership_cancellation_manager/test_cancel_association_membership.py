import datetime
from unittest.mock import patch, Mock, ANY

from tapir.associations.models import AssociationMembershipDeletedLogEntry
from tapir.associations.services.association_membership_cancellation_manager import (
    AssociationMembershipCancellationManager,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestCancelAssociationMembership(TapirUnitTest):

    @patch.object(
        TapirCache,
        "get_member_association_memberships",
        autospec=True,
    )
    @patch.object(
        TapirCache,
        "get_member_association_membership_at_date",
        autospec=True,
    )
    @patch.object(
        AssociationMembershipCancellationManager,
        "_set_membership_end_date",
        autospec=True,
    )
    def test_cancelAssociationMembership_currentMembershipExists_membershipEndDateSet(
        self,
        mock_set_membership_end_date: Mock,
        mock_get_member_association_membership_at_date: Mock,
        mock_get_member_association_memberships: Mock,
    ):
        current_membership = Mock()
        member = Mock()
        end_date = Mock()
        actor = Mock()
        cache = Mock()

        mock_get_member_association_membership_at_date.return_value = current_membership
        mock_get_member_association_memberships.return_value = []

        AssociationMembershipCancellationManager.cancel_association_membership(
            member=member,
            end_date=end_date,
            actor=actor,
            cache=cache,
        )

        mock_get_member_association_membership_at_date.assert_called_once_with(
            cache=cache, member=member, reference_date=end_date
        )
        mock_set_membership_end_date.assert_called_once_with(
            membership=current_membership, end_date=end_date, actor=actor, cache=cache
        )
        mock_get_member_association_memberships.assert_called_once_with(
            member=member, cache=cache
        )
        current_membership.delete.assert_not_called()

    @patch.object(
        AssociationMembershipDeletedLogEntry, "populate_membership", autospec=True
    )
    @patch.object(
        TapirCache,
        "get_member_association_memberships",
        autospec=True,
    )
    @patch.object(
        TapirCache,
        "get_member_association_membership_at_date",
        autospec=True,
    )
    @patch.object(
        AssociationMembershipCancellationManager,
        "_set_membership_end_date",
        autospec=True,
    )
    def test_cancelAssociationMembership_futureMembershipExists_futureMembershipsDeleted(
        self,
        mock_set_membership_end_date: Mock,
        mock_get_member_association_membership_at_date: Mock,
        mock_get_member_association_memberships: Mock,
        mock_populate_membership: Mock,
    ):
        current_membership = None
        member = Mock()
        end_date = datetime.date(year=2010, month=12, day=31)
        actor = Mock()
        cache = Mock()

        mock_get_member_association_membership_at_date.return_value = current_membership
        future_membership = Mock(start_date=datetime.date(year=2011, month=1, day=1))
        past_membership = Mock(start_date=datetime.date(year=2010, month=1, day=1))
        mock_get_member_association_memberships.return_value = [
            future_membership,
            past_membership,
        ]

        AssociationMembershipCancellationManager.cancel_association_membership(
            member=member,
            end_date=end_date,
            actor=actor,
            cache=cache,
        )

        mock_get_member_association_membership_at_date.assert_called_once_with(
            cache=cache, member=member, reference_date=end_date
        )
        mock_set_membership_end_date.assert_not_called()
        mock_get_member_association_memberships.assert_called_once_with(
            member=member, cache=cache
        )
        past_membership.delete.assert_not_called()
        future_membership.delete.assert_called_once_with()

        mock_populate_membership.assert_called_once_with(
            ANY, membership=future_membership, actor=actor
        )
        mock_populate_membership.return_value.save.assert_called_once_with()
