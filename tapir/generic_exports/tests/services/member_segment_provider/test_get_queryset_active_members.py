import datetime

from django.utils import timezone

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    CoopShareTransactionFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetQuerysetActiveMembers(TapirIntegrationTest):
    def test_getQuerysetActiveMembers_memberNotActive_notIncluded(self):
        MemberFactory.create()

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=timezone.now()
        )

        self.assertQuerySetEqual(result, [])

    def test_getQuerysetActiveMembers_memberHasPastCoopShare_notIncluded(self):
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member,
            valid_at=datetime.date(year=2026, month=1, day=1),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            quantity=1,
        )
        CoopShareTransactionFactory.create(
            member=member,
            valid_at=datetime.date(year=2026, month=6, day=1),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
            quantity=-1,
        )

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=7, day=1, tzinfo=datetime.timezone.utc
            )
        )

        self.assertQuerySetEqual(result, [])

    def test_getQuerysetActiveMembers_memberHasCurrentCoopShare_included(self):
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member,
            valid_at=datetime.date(year=2026, month=1, day=1),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            quantity=1,
        )
        CoopShareTransactionFactory.create(
            member=member,
            valid_at=datetime.date(year=2026, month=6, day=1),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
            quantity=-1,
        )

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            )
        )

        self.assertQuerySetEqual(result, [member])

    def test_getQuerysetActiveMembers_memberHasFutureCoopShare_included(self):
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member,
            valid_at=datetime.date(year=2026, month=1, day=1),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            quantity=1,
        )

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=datetime.datetime(
                year=2025, month=4, day=1, tzinfo=datetime.timezone.utc
            )
        )

        self.assertQuerySetEqual(result, [member])

    def test_getQuerysetActiveMembers_memberHasPastSubscription_notIncluded(self):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member, period__start_date=datetime.date(year=2025, month=1, day=1)
        )

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=1, day=1, tzinfo=datetime.timezone.utc
            )
        )

        self.assertQuerySetEqual(result, [])

    def test_getQuerysetActiveMembers_memberHasCurrentSubscription_included(self):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member, period__start_date=datetime.date(year=2026, month=1, day=1)
        )

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            )
        )

        self.assertQuerySetEqual(result, [member])

    def test_getQuerysetActiveMembers_memberHasFutureSubscription_included(self):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member, period__start_date=datetime.date(year=2027, month=1, day=1)
        )

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            )
        )

        self.assertQuerySetEqual(result, [member])

    def test_getQuerysetActiveMembers_memberHasPastAssociationMembership_notIncluded(
        self,
    ):
        member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=3, day=15),
        )

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            )
        )

        self.assertQuerySetEqual(result, [])

    def test_getQuerysetActiveMembers_memberHasCurrentAssociationMembership_included(
        self,
    ):
        member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2026, month=1, day=1),
        )

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            )
        )

        self.assertQuerySetEqual(result, [member])

    def test_getQuerysetActiveMembers_memberHasFutureAssociationMembership_included(
        self,
    ):
        member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2027, month=1, day=1),
        )

        result = MemberSegmentProvider.get_queryset_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            )
        )

        self.assertQuerySetEqual(result, [member])
