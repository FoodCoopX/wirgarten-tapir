import datetime

from tapir.deliveries.tests.factories import JokerFactory
from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import Member, PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetQuerysetMembersWithHomeDeliveryThisWeek(TapirIntegrationTest):
    MONDAY = datetime.date(year=2031, month=4, day=14)
    DELIVERY_DATE = datetime.date(year=2031, month=4, day=16)
    REFERENCE_DATETIME = datetime.datetime(year=2031, month=4, day=14, hour=6)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(key=ParameterKeys.DELIVERY_DAY, value=2)
        cls._set_parameter(key=ParameterKeys.JOKERS_ENABLED, value=True)

    def setUp(self):
        super().setUp()
        mock_timezone(test=self, now=self.REFERENCE_DATETIME)
        self.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2031, month=1, day=1),
            end_date=datetime.date(year=2031, month=12, day=31),
        )
        self.product_type = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        self.home_delivery_location = PickupLocationFactory.create(
            is_home_delivery=True
        )

    def _create_member_with_subscription(
        self, pickup_location: PickupLocation
    ) -> Member:
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member, period=self.growing_period, product__type=self.product_type
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=self.growing_period.start_date,
        )
        return member

    def _get_members(self) -> list[Member]:
        return list(
            MemberSegmentProvider.get_queryset_members_with_home_delivery_this_week(
                self.REFERENCE_DATETIME
            )
        )

    def test_getQuerysetMembersWithHomeDeliveryThisWeek_memberAtHomeDeliveryLocation_memberIncluded(
        self,
    ):
        member = self._create_member_with_subscription(
            pickup_location=self.home_delivery_location
        )

        self.assertEqual([member], self._get_members())

    def test_getQuerysetMembersWithHomeDeliveryThisWeek_memberAtNormalLocation_memberNotIncluded(
        self,
    ):
        self._create_member_with_subscription(
            pickup_location=PickupLocationFactory.create()
        )

        self.assertEqual([], self._get_members())

    def test_getQuerysetMembersWithHomeDeliveryThisWeek_memberHasJoker_memberNotIncluded(
        self,
    ):
        member = self._create_member_with_subscription(
            pickup_location=self.home_delivery_location
        )
        JokerFactory.create(member=member, date=self.DELIVERY_DATE)

        self.assertEqual([], self._get_members())

    def test_getQuerysetMembersWithHomeDeliveryThisWeek_homeDeliveryStartsNextWeek_memberNotIncluded(
        self,
    ):
        member = self._create_member_with_subscription(
            pickup_location=PickupLocationFactory.create()
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.home_delivery_location,
            valid_from=self.MONDAY + datetime.timedelta(days=7),
        )

        self.assertEqual([], self._get_members())

    def test_getQuerysetMembersWithHomeDeliveryThisWeek_homeDeliveryEndsNextWeek_memberIncluded(
        self,
    ):
        member = self._create_member_with_subscription(
            pickup_location=self.home_delivery_location
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=PickupLocationFactory.create(),
            valid_from=self.MONDAY + datetime.timedelta(days=7),
        )

        self.assertEqual([member], self._get_members())

    def test_getQuerysetMembersWithHomeDeliveryThisWeek_noSubscription_memberNotIncluded(
        self,
    ):
        MemberPickupLocationFactory.create(
            pickup_location=self.home_delivery_location,
            valid_from=self.growing_period.start_date,
        )

        self.assertEqual([], self._get_members())
