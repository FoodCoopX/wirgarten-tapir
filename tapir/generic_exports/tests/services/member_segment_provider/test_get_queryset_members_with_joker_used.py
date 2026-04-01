import datetime

from tapir.deliveries.models import Joker
from tapir.generic_exports.services.export_segment_manager import ExportSegmentManager
from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import GrowingPeriodFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetQuerysetMembersWithJokerUsed(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2022, month=1, day=1),
            end_date=datetime.date(year=2022, month=12, day=31),
        )
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        for date in [
            datetime.date(year=2022, month=5, day=5),
            datetime.date(year=2023, month=10, day=6),
            datetime.date(year=2023, month=12, day=7),
        ]:
            member = MemberFactory.create()
            Joker.objects.create(member=member, date=date)

    def test_segment_is_included_in_registered_segments(self):
        segment = ExportSegmentManager.get_segment_by_id("members.with_used_joker")
        self.assertEqual(
            MemberSegmentProvider.get_queryset_members_with_joker_used,
            segment.get_queryset,
        )

    def test_getQuerysetMembersWithJokerUsed_memberHasNoJokerInGivenPeriod_memberNotIncluded(
        self,
    ):
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2022, month=4, day=5)
        )

        queryset = MemberSegmentProvider.get_queryset_members_with_joker_used(
            datetime.datetime(year=2023, month=4, day=5)
        )

        self.assertNotIn(member, queryset)

    def test_getQuerysetMembersWithJokerUsed_memberHasAJokerInGivenPeriodButAfterGivenDate_memberNotIncluded(
        self,
    ):
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2023, month=12, day=5)
        )

        queryset = MemberSegmentProvider.get_queryset_members_with_joker_used(
            datetime.datetime(year=2023, month=4, day=5)
        )

        self.assertNotIn(member, queryset)

    def test_getQuerysetMembersWithJokerUsed_memberHasAJokerInGivenPeriodAndAfterGivenDate_memberIncluded(
        self,
    ):
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2023, month=3, day=7)
        )

        queryset = MemberSegmentProvider.get_queryset_members_with_joker_used(
            datetime.datetime(year=2023, month=4, day=5)
        )

        self.assertIn(member, queryset)
