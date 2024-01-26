import datetime

from dateutil.relativedelta import relativedelta
from tapir.wirgarten.utils import get_today
from tapir_mail.service.segment import resolve_segments

from tapir.wirgarten.tapirmail import (
    Filters,
    Segments,
    _register_filters,
    _register_segments,
)
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    MemberWithSubscriptionFactory,
    PickupLocationFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    mock_timezone,
    set_bypass_keycloak,
)


class SegmentFilterTest(TapirIntegrationTest):
    NOW = datetime.datetime(2023, 4, 15, 12, 0, tzinfo=datetime.timezone.utc)

    def setUp(self):
        mock_timezone(self, self.NOW)
        set_bypass_keycloak()

        self.current_growing_period = GrowingPeriodFactory.create()
        next_start = self.current_growing_period.end_date + relativedelta(days=1)
        self.next_growing_period = GrowingPeriodFactory.create(
            start_date=next_start,
            end_date=next_start + relativedelta(years=1),
        )
        self.included_pickup_location = PickupLocationFactory.create()
        self.excluded_pickup_location = PickupLocationFactory.create(coords_lat=1.0)

        _register_segments()
        _register_filters()

    def ids(self, collection):
        return set([m.id for m in collection])

    def test_combineFiltersWithSegment_contractExtendedYes_correctResult(self):
        included_member = MemberWithSubscriptionFactory.create(id="ext_yes")
        subscription = SubscriptionFactory.create(
            period=self.next_growing_period,
            member=included_member,
        )
        excluded_member = MemberWithSubscriptionFactory.create(id="ext_no")

        expected_member_ids = [
            included_member.id,
        ]

        segment_members = resolve_segments(
            add_segments=[Segments.WITH_ACTIVE_SUBSCRIPTION],
            filter_list=[Filters.CONTRACT_EXTENDED_YES],
        )

        self.assertSetEqual(
            self.ids(segment_members),
            set(expected_member_ids),
        )

    def test_combineFiltersWithSegment_contractExtendedNo_correctResult(self):
        # Member who cancels to the end of the current growing period
        included_member = MemberFactory.create()
        SubscriptionFactory.create(
            member=included_member,
            start_date=self.current_growing_period.start_date,
            end_date=self.current_growing_period.end_date,
            cancellation_ts=self.NOW.date(),
        )

        # Member who does not cancel
        excluded_member = MemberWithSubscriptionFactory.create()

        expected_member_ids = [included_member.id]

        segment_members = resolve_segments(
            add_segments=[Segments.WITH_ACTIVE_SUBSCRIPTION],
            filter_list=[Filters.CONTRACT_EXTENDED_NO],
        )

        self.assertSetEqual(self.ids(segment_members), set(expected_member_ids))

    def test_combineFiltersWithSegment_contractExtendedNoReaction_correctResult(self):
        # Member with no reaction after the trial period
        included_member = MemberWithSubscriptionFactory.create()

        # Member who is still in the trial period
        trial_member = MemberFactory.create()
        SubscriptionFactory.create(
            member=trial_member,
            start_date=get_today() + relativedelta(day=1),
        )

        # Member who renewed the subscription
        renewed_member = MemberWithSubscriptionFactory.create()
        SubscriptionFactory.create(
            member=renewed_member,
            period=self.next_growing_period,
            # This member extends the subscription into the next growing period
        )

        # Member who cancels to the end of the current growing period
        cancelled_member = MemberFactory.create()
        SubscriptionFactory.create(
            member=cancelled_member,
            cancellation_ts=self.NOW.date(),
        )

        expected_member_ids = [included_member.id]

        segment_members = resolve_segments(
            add_segments=[Segments.WITH_ACTIVE_SUBSCRIPTION],
            filter_list=[Filters.CONTRACT_EXTENDED_NO_REACTION],
        )

        self.assertSetEqual(self.ids(segment_members), set(expected_member_ids))

    def test_filterByPickupLocation_correctResult(self):
        # Create different pickup locations and members associated with them
        included_member = MemberWithSubscriptionFactory.create()
        excluded_member = MemberWithSubscriptionFactory.create()

        MemberPickupLocationFactory.create(
            member=included_member,
            pickup_location=self.included_pickup_location,
        )
        MemberPickupLocationFactory.create(
            member=excluded_member,
            pickup_location=self.excluded_pickup_location,
        )

        filter_name = f"Abholort: {self.included_pickup_location.name}"
        expected_member_ids = {included_member.id}

        segment_members = resolve_segments(
            add_segments=[Segments.WITH_ACTIVE_SUBSCRIPTION],
            filter_list=[filter_name],
        )

        self.assertSetEqual(self.ids(segment_members), expected_member_ids)
