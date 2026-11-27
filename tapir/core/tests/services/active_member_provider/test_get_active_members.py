import datetime
from decimal import Decimal

from django.utils import timezone

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.services.active_member_provider import ActiveMemberProvider
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    CoopShareTransactionFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetActiveMembers(TapirIntegrationTest):
    def test_getActiveMembers_memberNotActive_notIncluded(self):
        MemberFactory.create()

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=timezone.now(), cache={}
        )

        self.assertQuerySetEqual(result, [])

    def test_getActiveMembers_memberHasPastCoopShare_notIncluded(self):
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

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=7, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [])

    def test_getActiveMembers_memberHasCurrentCoopShare_included(self):
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

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [member])

    def test_getActiveMembers_memberHasFutureCoopShare_included(self):
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member,
            valid_at=datetime.date(year=2026, month=1, day=1),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            quantity=1,
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2025, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [member])

    def test_getActiveMembers_memberHasPastSubscription_notIncluded(self):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member, period__start_date=datetime.date(year=2025, month=1, day=1)
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=1, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [])

    def test_getActiveMembers_memberHasCurrentSubscription_included(self):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member, period__start_date=datetime.date(year=2026, month=1, day=1)
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [member])

    def test_getActiveMembers_memberHasFutureSubscription_included(self):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member, period__start_date=datetime.date(year=2027, month=1, day=1)
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [member])

    def test_getActiveMembers_memberHasPastAssociationMembership_notIncluded(
        self,
    ):
        member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=3, day=15),
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [])

    def test_getActiveMembers_memberHasCurrentAssociationMembership_included(
        self,
    ):
        member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2026, month=1, day=1),
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [member])

    def test_getActiveMembers_memberHasFutureAssociationMembership_included(
        self,
    ):
        member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2027, month=1, day=1),
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [member])

    def test_getActiveMembers_memberHasPastSolidarityContribution_notIncluded(
        self,
    ):
        member = MemberFactory.create()
        SolidarityContributionFactory.create(
            member=member,
            amount=Decimal(10),
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=3, day=15),
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [])

    def test_getActiveMembers_memberHasCurrentSolidarityContribution_included(
        self,
    ):
        member = MemberFactory.create()
        SolidarityContributionFactory.create(
            member=member,
            amount=Decimal(10),
            start_date=datetime.date(year=2026, month=1, day=1),
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [member])

    def test_getActiveMembers_memberHasFutureSolidarityContribution_included(
        self,
    ):
        member = MemberFactory.create()
        SolidarityContributionFactory.create(
            member=member,
            amount=Decimal(10),
            start_date=datetime.date(year=2027, month=1, day=1),
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [member])

    def test_getActiveMembers_memberHasNegativeSolidarityContribution_notIncluded(
        self,
    ):
        member = MemberFactory.create()
        SolidarityContributionFactory.create(
            member=member,
            amount=Decimal(-10),
            start_date=datetime.date(year=2026, month=1, day=1),
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [])

    def test_getActiveMembers_memberHasZeroSolidarityContribution_notIncluded(
        self,
    ):
        member = MemberFactory.create()
        SolidarityContributionFactory.create(
            member=member,
            amount=Decimal(0),
            start_date=datetime.date(year=2026, month=1, day=1),
        )

        result = ActiveMemberProvider.get_active_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [])
