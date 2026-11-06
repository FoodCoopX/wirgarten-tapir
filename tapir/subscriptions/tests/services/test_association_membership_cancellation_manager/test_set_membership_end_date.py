import datetime

from tapir.associations.models import AssociationMembershipUpdatedLogEntry
from tapir.associations.services.association_membership_cancellation_manager import (
    AssociationMembershipCancellationManager,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestSetMembershipEndDate(TapirIntegrationTest):
    def test_setMembershipEndDate_default_setsEndDateAndCreatesLogEntry(self):
        now = mock_timezone(self, datetime.datetime(2019, 6, 12))
        membership = AssociationMembershipFactory(
            start_date=datetime.date(2019, 1, 1), end_date=None, cancellation_ts=None
        )
        end_date = datetime.date(2019, 12, 31)
        AssociationMembershipCancellationManager._set_membership_end_date(
            membership, end_date, membership.member, {}
        )
        membership.refresh_from_db()
        self.assertEqual(end_date, membership.end_date)
        self.assertEqual(now, membership.cancellation_ts)
        entry = AssociationMembershipUpdatedLogEntry.objects.get()
        self.assertEqual(membership.member_id, entry.actor_id)
        self.assertEqual(membership.member_id, entry.user_id)
