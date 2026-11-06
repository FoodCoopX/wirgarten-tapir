import datetime

from tapir.associations.models import (
    AssociationMembership,
    AssociationMembershipDeletedLogEntry,
    AssociationMembershipUpdatedLogEntry,
)
from tapir.associations.services.association_membership_cancellation_manager import (
    AssociationMembershipCancellationManager,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCancelAssociationMembership(TapirIntegrationTest):
    def test_cancelAssociationMembership_currentMembershipExists_membershipEndDateSet(
        self,
    ):
        membership = AssociationMembershipFactory(
            start_date=datetime.date(2010, 1, 1), end_date=None
        )
        end_date = datetime.date(2010, 12, 31)
        AssociationMembershipCancellationManager.cancel_association_membership(
            membership.member, end_date, membership.member, {}
        )
        membership.refresh_from_db()
        self.assertEqual(end_date, membership.end_date)
        self.assertIsNotNone(membership.cancellation_ts)
        self.assertEqual(1, AssociationMembershipUpdatedLogEntry.objects.count())
        self.assertTrue(AssociationMembership.objects.filter(pk=membership.pk).exists())

    def test_cancelAssociationMembership_futureMembershipExists_futureMembershipsDeleted(
        self,
    ):
        past = AssociationMembershipFactory(
            start_date=datetime.date(2010, 1, 1), end_date=datetime.date(2010, 12, 1)
        )
        future = AssociationMembershipFactory(
            member=past.member, start_date=datetime.date(2011, 1, 1)
        )
        before = dict(AssociationMembership.objects.filter(pk=past.pk).values().get())
        AssociationMembershipCancellationManager.cancel_association_membership(
            past.member, datetime.date(2010, 12, 31), past.member, {}
        )
        self.assertFalse(AssociationMembership.objects.filter(pk=future.pk).exists())
        self.assertEqual(
            before,
            dict(AssociationMembership.objects.filter(pk=past.pk).values().get()),
        )
        entry = AssociationMembershipDeletedLogEntry.objects.get()
        self.assertEqual(past.member_id, entry.user_id)
        self.assertEqual(past.member_id, entry.actor_id)
        self.assertFalse(AssociationMembershipUpdatedLogEntry.objects.exists())
