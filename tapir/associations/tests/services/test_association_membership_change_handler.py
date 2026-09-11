import datetime

from tapir.associations.models import (
    AssociationMembership,
    AssociationMembershipCreatedLogEntry,
    AssociationMembershipDeletedLogEntry,
    AssociationMembershipUpdatedLogEntry,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.associations.tests.factories import (
    AssociationMembershipTypeFactory,
    AssociationMembershipFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationMembershipChangeHandler(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.association_membership_type = AssociationMembershipTypeFactory.create()

    def test_startMembership_memberHadNoMembership_createsMembershipAndLogEntry(self):
        member = MemberFactory.create()
        actor = MemberFactory.create()
        start_date = datetime.date(year=2037, month=2, day=26)

        AssociationMembershipChangeHandler.start_membership(
            member=member,
            association_membership_type=self.association_membership_type,
            start_date=start_date,
            actor=actor,
            cache={},
        )

        self.assertEqual(1, AssociationMembership.objects.count())
        membership = AssociationMembership.objects.get()
        self.assertEqual(member.id, membership.member_id)
        self.assertEqual(self.association_membership_type.id, membership.type_id)
        self.assertEqual(start_date, membership.start_date)
        self.assertIsNone(membership.end_date)

        self.assertEqual(1, AssociationMembershipCreatedLogEntry.objects.count())
        log_entry = AssociationMembershipCreatedLogEntry.objects.get()
        self.assertEqual(self.association_membership_type.name, log_entry.type_name)
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)

        self.assertFalse(AssociationMembershipDeletedLogEntry.objects.exists())
        self.assertFalse(AssociationMembershipUpdatedLogEntry.objects.exists())

    def test_startMembership_memberHadAnExpiredMembership_expiredMembershipNotChanged(
        self,
    ):
        member = MemberFactory.create()
        actor = MemberFactory.create()
        start_date = datetime.date(year=2037, month=2, day=26)
        expired_membership_before_changes = AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2037, month=1, day=1),
            end_date=datetime.date(year=2037, month=2, day=15),
        )

        AssociationMembershipChangeHandler.start_membership(
            member=member,
            association_membership_type=self.association_membership_type,
            start_date=start_date,
            actor=actor,
            cache={},
        )

        self.assertEqual(2, AssociationMembership.objects.count())
        expired_membership_after_changes, new_membership = (
            AssociationMembership.objects.order_by("start_date")
        )
        self.assertEqual(member.id, new_membership.member_id)
        self.assertEqual(self.association_membership_type.id, new_membership.type_id)
        self.assertEqual(start_date, new_membership.start_date)

        self.assertEqual(member.id, expired_membership_after_changes.member_id)
        self.assertEqual(
            expired_membership_before_changes.type_id,
            expired_membership_after_changes.type_id,
        )
        self.assertEqual(
            expired_membership_before_changes.end_date,
            expired_membership_after_changes.end_date,
        )
        self.assertEqual(
            expired_membership_before_changes.start_date,
            expired_membership_after_changes.start_date,
        )

        self.assertEqual(1, AssociationMembershipCreatedLogEntry.objects.count())
        log_entry = AssociationMembershipCreatedLogEntry.objects.get()
        self.assertEqual(self.association_membership_type.name, log_entry.type_name)
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)

        self.assertFalse(AssociationMembershipDeletedLogEntry.objects.exists())
        self.assertFalse(AssociationMembershipUpdatedLogEntry.objects.exists())

    def test_startMembership_memberHadAFutureMembership_futureMembershipDeletedAnLogEntryCreated(
        self,
    ):
        member = MemberFactory.create()
        actor = MemberFactory.create()
        start_date = datetime.date(year=2037, month=2, day=26)
        future_membership = AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2037, month=6, day=1),
        )

        AssociationMembershipChangeHandler.start_membership(
            member=member,
            association_membership_type=self.association_membership_type,
            start_date=start_date,
            actor=actor,
            cache={},
        )

        self.assertEqual(1, AssociationMembership.objects.count())
        membership = AssociationMembership.objects.get()
        self.assertEqual(member.id, membership.member_id)
        self.assertEqual(self.association_membership_type.id, membership.type_id)
        self.assertEqual(start_date, membership.start_date)
        self.assertIsNone(membership.end_date)

        self.assertEqual(1, AssociationMembershipDeletedLogEntry.objects.count())
        log_entry = AssociationMembershipDeletedLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)
        self.assertEqual(future_membership.start_date, log_entry.start_date)
        self.assertEqual(future_membership.end_date, log_entry.end_date)
        self.assertEqual(future_membership.type.name, log_entry.type_name)

        self.assertFalse(AssociationMembershipUpdatedLogEntry.objects.exists())

    def test_startMembership_memberHadAnOnGoingMembership_ongoingMembershipEndedAndLogEntryCreated(
        self,
    ):
        member = MemberFactory.create()
        actor = MemberFactory.create()
        start_date = datetime.date(year=2037, month=2, day=26)
        ongoing_membership = AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2037, month=1, day=1),
        )
        now = mock_timezone(
            test=self, now=datetime.datetime(year=2036, month=12, day=18)
        )

        AssociationMembershipChangeHandler.start_membership(
            member=member,
            association_membership_type=self.association_membership_type,
            start_date=start_date,
            actor=actor,
            cache={},
        )

        self.assertEqual(2, AssociationMembership.objects.count())
        membership = AssociationMembership.objects.order_by("start_date").last()
        self.assertEqual(member.id, membership.member_id)
        self.assertEqual(self.association_membership_type.id, membership.type_id)
        self.assertEqual(start_date, membership.start_date)
        self.assertIsNone(membership.cancellation_ts)
        self.assertIsNone(membership.end_date)

        ongoing_membership.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2037, month=2, day=25), ongoing_membership.end_date
        )
        self.assertEqual(now, ongoing_membership.cancellation_ts)
        self.assertEqual(1, AssociationMembershipUpdatedLogEntry.objects.count())
        log_entry = AssociationMembershipUpdatedLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)
        self.assertEqual("None", log_entry.old_values["end_date"])
        self.assertEqual(
            str(ongoing_membership.end_date), log_entry.new_values["end_date"]
        )

        self.assertFalse(AssociationMembershipDeletedLogEntry.objects.exists())
