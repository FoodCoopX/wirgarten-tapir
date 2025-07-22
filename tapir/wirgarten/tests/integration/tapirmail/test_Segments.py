import datetime

from dateutil.relativedelta import relativedelta
from tapir_mail.service.segment import resolve_segments

from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import Segments, _register_segments
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberWithCoopSharesFactory,
    MemberWithSubscriptionFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    mock_timezone,
    set_bypass_keycloak,
)


class SegmentTest(TapirIntegrationTest):
    NOW = datetime.datetime(2023, 4, 15, 12, 0, tzinfo=datetime.timezone.utc)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def setUp(self):
        mock_timezone(self, self.NOW)
        set_bypass_keycloak()

        _register_segments()

        self.create_test_data()

    def create_test_data(self):
        self.member_without_shares = MemberFactory.create(id="no_shares")
        self.member_with_shares = MemberWithCoopSharesFactory.create(id="has_shares")
        self.member_with_subscription = MemberWithSubscriptionFactory.create(
            id="has_sub"
        )

    @staticmethod
    def ids(collection):
        return set([m.id for m in collection])

    def test_resolveSegment_coopMembers_correctResult(self):
        expected_member_ids = [
            self.member_with_shares.id,
            self.member_with_subscription.id,
        ]
        segment_members = resolve_segments(add_segments=[Segments.COOP_MEMBERS])

        self.assertSetEqual(self.ids(segment_members), set(expected_member_ids))

    def test_resolveSegment_nonCoopMembers_correctResult(self):
        expected_member_ids = [self.member_without_shares.id]
        segment_members = resolve_segments(add_segments=[Segments.NON_COOP_MEMBERS])
        self.assertSetEqual(self.ids(segment_members), set(expected_member_ids))

    def test_resolveSegment_withActiveSubscription_correctResult(self):
        expected_member_ids = [self.member_with_subscription.id]
        segment_members = resolve_segments(
            add_segments=[Segments.WITH_ACTIVE_SUBSCRIPTION]
        )

        self.assertSetEqual(self.ids(segment_members), set(expected_member_ids))

    def test_resolveSegment_withoutActiveSubscription_correctResult(self):
        expected_member_ids = [
            self.member_without_shares.id,
            self.member_with_shares.id,
        ]
        segment_members = resolve_segments(
            add_segments=[Segments.WITHOUT_ACTIVE_SUBSCRIPTION]
        )

        self.assertSetEqual(self.ids(segment_members), set(expected_member_ids))

    def test_resolveSegment_withActiveSubscriptionStartsInFuture_memberIsNotIncluded(
        self,
    ):
        expected_member_ids = [self.member_with_subscription.id]
        start_date_next_month = (
            ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=self.NOW.date(), cache={}
            )
        )

        edge_case_member = MemberFactory.create()
        SubscriptionFactory.create(
            member=edge_case_member,
            start_date=start_date_next_month,
            end_date=start_date_next_month + relativedelta(months=1),
        )
        segment_members = resolve_segments(
            add_segments=[Segments.WITH_ACTIVE_SUBSCRIPTION]
        )

        self.assertSetEqual(self.ids(segment_members), set(expected_member_ids))

    def test_resolveSegment_dateHasChangedSinceSegmentRegistration_correctResult(self):
        subscription = Subscription.objects.get()
        subscription.end_date = self.NOW + datetime.timedelta(days=15)
        subscription.save()

        expected_member_ids = [self.member_with_subscription.id]
        segment_members = resolve_segments(
            add_segments=[Segments.WITH_ACTIVE_SUBSCRIPTION]
        )
        self.assertSetEqual(self.ids(segment_members), set(expected_member_ids))

        mock_timezone(self, self.NOW + datetime.timedelta(days=30))

        expected_member_ids = set()
        segment_members = resolve_segments(
            add_segments=[Segments.WITH_ACTIVE_SUBSCRIPTION]
        )
        self.assertSetEqual(self.ids(segment_members), expected_member_ids)
