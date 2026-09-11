import datetime

from django.core.exceptions import ValidationError

from tapir.associations.services.association_membership_cancellation_manager import (
    AssociationMembershipCancellationManager,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import SubscriptionFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetEarliestPossibleMembershipCancellationDate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2020, month=6, day=1)
        )

    def test_getEarliestPossibleMembershipCancellationDate_oneUncancelledSubscriptionExists_raisesValidationError(
        self,
    ):
        subscription = SubscriptionFactory.create(
            cancellation_ts=None,
            period__start_date=datetime.date(year=2020, month=1, day=1),
        )

        with self.assertRaises(ValidationError) as error:
            AssociationMembershipCancellationManager.get_earliest_possible_membership_cancellation_date(
                member=subscription.member, cache={}
            )

        self.assertEqual("Dieses Mitglied hat aktive Verträge", error.exception.message)

    def test_getEarliestPossibleMembershipCancellationDate_oneUncancelledPastSubscriptionExists_subscriptionIgnored(
        self,
    ):
        subscription = SubscriptionFactory.create(
            cancellation_ts=None,
            period__start_date=datetime.date(year=2019, month=1, day=1),
        )

        result = AssociationMembershipCancellationManager.get_earliest_possible_membership_cancellation_date(
            member=subscription.member, cache={}
        )

        self.assertEqual(self.now.date(), result)

    def test_getEarliestPossibleMembershipCancellationDate_noRelevantSubscription_returnsToday(
        self,
    ):
        result = AssociationMembershipCancellationManager.get_earliest_possible_membership_cancellation_date(
            member=MemberFactory.create(), cache={}
        )

        self.assertEqual(self.now.date(), result)

    def test_getEarliestPossibleMembershipCancellationDate_severalRelevantSubscriptions_returnsLatestEndDate(
        self,
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            cancellation_ts=self.now,
            period__start_date=datetime.date(year=2020, month=1, day=1),
            end_date=datetime.date(year=2020, month=6, day=15),
        )
        SubscriptionFactory.create(
            member=member,
            cancellation_ts=self.now,
            period__start_date=datetime.date(year=2020, month=1, day=1),
            end_date=datetime.date(year=2020, month=7, day=28),
        )
        latest_subscription = SubscriptionFactory.create(
            member=member,
            cancellation_ts=self.now,
            period__start_date=datetime.date(year=2020, month=1, day=1),
            end_date=datetime.date(year=2020, month=9, day=6),
        )

        result = AssociationMembershipCancellationManager.get_earliest_possible_membership_cancellation_date(
            member=member, cache={}
        )

        self.assertEqual(latest_subscription.end_date, result)
