import datetime
from unittest.mock import Mock

from tapir.associations.services.association_membership_cancellation_manager import (
    AssociationMembershipCancellationManager,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestCanMembershipBeCancelled(TapirUnitTest):
    def test_canMembershipBeCancelled_membershipAlreadyCancelled_returnsFalse(self):
        membership = AssociationMembershipFactory.build(cancellation_ts=Mock())

        self.assertFalse(
            AssociationMembershipCancellationManager._can_membership_be_cancelled(
                membership=membership, reference_date=Mock()
            )
        )

    def test_canMembershipBeCancelled_endDateIsInThePast_returnsFalse(self):
        membership = AssociationMembershipFactory.build(
            cancellation_ts=None, end_date=datetime.date(year=2022, month=6, day=29)
        )

        self.assertFalse(
            AssociationMembershipCancellationManager._can_membership_be_cancelled(
                membership=membership,
                reference_date=datetime.date(year=2022, month=6, day=30),
            )
        )

    def test_canMembershipBeCancelled_endDateIsOnGivenDate_returnsFalse(self):
        membership = AssociationMembershipFactory.build(
            cancellation_ts=None, end_date=datetime.date(year=2022, month=6, day=29)
        )

        self.assertFalse(
            AssociationMembershipCancellationManager._can_membership_be_cancelled(
                membership=membership,
                reference_date=datetime.date(year=2022, month=6, day=29),
            )
        )

    def test_canMembershipBeCancelled_endDateIsInTheFuture_returnsTrue(self):
        membership = AssociationMembershipFactory.build(
            cancellation_ts=None, end_date=datetime.date(year=2022, month=6, day=29)
        )

        self.assertTrue(
            AssociationMembershipCancellationManager._can_membership_be_cancelled(
                membership=membership,
                reference_date=datetime.date(year=2022, month=6, day=28),
            )
        )

    def test_canMembershipBeCancelled_endDateIsNotSet_returnsTrue(self):
        membership = AssociationMembershipFactory.build(
            cancellation_ts=None, end_date=None
        )

        self.assertTrue(
            AssociationMembershipCancellationManager._can_membership_be_cancelled(
                membership=membership,
                reference_date=datetime.date(year=2022, month=6, day=30),
            )
        )
