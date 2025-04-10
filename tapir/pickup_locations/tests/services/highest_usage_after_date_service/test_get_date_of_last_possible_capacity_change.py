import datetime

from tapir.pickup_locations.services.highest_usage_after_date_service import (
    HighestUsageAfterDateService,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    PickupLocationFactory,
    MemberPickupLocationFactory,
    MemberFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetDateOfLastPossibleCapacityChange(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_getDateOfLastPossibleCapacityChange_noMemberPickupLocation_returnsEndDateOfLatestSubscription(
        self,
    ):
        SubscriptionFactory.create(end_date=datetime.date(year=2023, month=5, day=12))
        SubscriptionFactory.create(end_date=datetime.date(year=2023, month=12, day=8))
        SubscriptionFactory.create(end_date=datetime.date(year=2023, month=7, day=6))

        result = HighestUsageAfterDateService.get_date_of_last_possible_capacity_change(
            pickup_location=PickupLocationFactory.create(), cache={}
        )

        self.assertEqual(datetime.date(year=2023, month=12, day=8), result)

    def test_getDateOfLastPossibleCapacityChange_noSubscription_returnsDateOfLastRelevantPickupLocationChange(
        self,
    ):
        pickup_location = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            pickup_location=pickup_location,
            valid_from=datetime.date(year=2023, month=5, day=12),
        )
        MemberPickupLocationFactory.create(
            pickup_location=pickup_location,
            valid_from=datetime.date(year=2023, month=6, day=7),
        )
        MemberPickupLocationFactory.create(
            pickup_location=PickupLocationFactory.create(),
            valid_from=datetime.date(year=2023, month=7, day=28),
        )

        result = HighestUsageAfterDateService.get_date_of_last_possible_capacity_change(
            pickup_location=pickup_location, cache={}
        )

        self.assertEqual(datetime.date(year=2023, month=6, day=7), result)

    def test_getDateOfLastPossibleCapacityChange_lastChangeIsFromPickupLocation_returnsPickupLocationDate(
        self,
    ):
        pickup_location = PickupLocationFactory.create()
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=datetime.date(year=2023, month=5, day=13),
        )
        SubscriptionFactory.create(
            member=member, end_date=datetime.date(year=2023, month=5, day=12)
        )

        result = HighestUsageAfterDateService.get_date_of_last_possible_capacity_change(
            pickup_location=pickup_location, cache={}
        )

        self.assertEqual(datetime.date(year=2023, month=5, day=13), result)

    def test_getDateOfLastPossibleCapacityChange_lastChangeIsFromSubscription_returnsSubscriptionEndDate(
        self,
    ):
        pickup_location = PickupLocationFactory.create()
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=datetime.date(year=2023, month=5, day=13),
        )
        SubscriptionFactory.create(
            member=member, end_date=datetime.date(year=2023, month=5, day=14)
        )

        result = HighestUsageAfterDateService.get_date_of_last_possible_capacity_change(
            pickup_location=pickup_location, cache={}
        )

        self.assertEqual(datetime.date(year=2023, month=5, day=14), result)
