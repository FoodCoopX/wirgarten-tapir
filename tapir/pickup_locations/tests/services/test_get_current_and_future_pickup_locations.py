import datetime

from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetCurrentAndFuturePickupLocations(TapirIntegrationTest):
    REFERENCE_DATE = datetime.date(year=2027, month=6, day=15)

    def test_getCurrentAndFuturePickupLocations_pastCurrentAndFuture_returnsCurrentAndFuture(
        self,
    ):
        member = MemberFactory.create()
        past, current, future = PickupLocationFactory.create_batch(size=3)
        for pickup_location, valid_from in [
            (past, datetime.date(year=2027, month=1, day=1)),
            (current, datetime.date(year=2027, month=3, day=1)),
            (future, datetime.date(year=2027, month=7, day=1)),
        ]:
            MemberPickupLocationFactory.create(
                member=member, pickup_location=pickup_location, valid_from=valid_from
            )

        result = MemberPickupLocationGetter.get_current_and_future_pickup_locations(
            member_id=member.id, reference_date=self.REFERENCE_DATE, cache={}
        )

        self.assertEqual([future, current], result)

    def test_getCurrentAndFuturePickupLocations_noPickupLocation_returnsEmptyList(
        self,
    ):
        member = MemberFactory.create()

        result = MemberPickupLocationGetter.get_current_and_future_pickup_locations(
            member_id=member.id, reference_date=self.REFERENCE_DATE, cache={}
        )

        self.assertEqual([], result)

    def test_getCurrentAndFuturePickupLocations_currentLinkIsNone_skipsIt(self):
        member = MemberFactory.create()
        future = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=None,
            valid_from=datetime.date(year=2027, month=3, day=1),
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=future,
            valid_from=datetime.date(year=2027, month=7, day=1),
        )

        result = MemberPickupLocationGetter.get_current_and_future_pickup_locations(
            member_id=member.id, reference_date=self.REFERENCE_DATE, cache={}
        )

        self.assertEqual([future], result)

    def test_getCurrentAndFutureHomeDeliveryLocations_mixedLocations_returnsOnlyHomeDelivery(
        self,
    ):
        member = MemberFactory.create()
        normal = PickupLocationFactory.create(is_home_delivery=False)
        home_delivery = PickupLocationFactory.create(is_home_delivery=True)
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=normal,
            valid_from=datetime.date(year=2027, month=3, day=1),
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=home_delivery,
            valid_from=datetime.date(year=2027, month=7, day=1),
        )

        result = (
            MemberPickupLocationGetter.get_current_and_future_home_delivery_locations(
                member_id=member.id, reference_date=self.REFERENCE_DATE, cache={}
            )
        )

        self.assertEqual([home_delivery], result)
