from django.test import override_settings

from tapir.bakery.services.breaddelivery_service import BreadDeliveryService
from tapir.bakery.tests.factories import (
    BreadDeliveryFactory,
    BreadFactory,
    offer_bread_at_pickup_location,
)
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(BAKERY_ENABLED=True)
class TestClearBreadsUnavailableAtPickupLocation(TapirIntegrationTest):
    """A choice kept on a station change must fit the new day's limit."""

    # Far enough ahead that no day of it is over.
    FUTURE_YEAR = 2099
    WEEK = 10
    DAY = 1

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.station = create_pickup_location_with_opening_times(open_days=[self.DAY])

    def _bread(self, max_pieces):
        bread = BreadFactory.create(
            name="Saaten", max_pieces=max_pieces, min_remaining_pieces=0
        )
        offer_bread_at_pickup_location(
            bread, self.station, year=self.FUTURE_YEAR, delivery_week=self.WEEK
        )
        return bread

    def _choice(self, bread):
        return BreadDeliveryFactory.create(
            year=self.FUTURE_YEAR,
            delivery_week=self.WEEK,
            pickup_location=self.station,
            bread=bread,
        )

    def _recheck(self, delivery):
        BreadDeliveryService.clear_breads_unavailable_at_pickup_location(
            delivery.subscription.member, cache={}
        )
        delivery.refresh_from_db()

    def test_clearBreadsUnavailableAtPickupLocation_keptChoiceOverTheNewDaysLimit_clearsIt(
        self,
    ):
        bread = self._bread(max_pieces=2)
        others = [self._choice(bread) for _ in range(2)]
        mover = self._choice(bread)

        self._recheck(mover)

        self.assertIsNone(mover.bread_id)
        for other in others:
            other.refresh_from_db()
            self.assertEqual(other.bread_id, bread.id)

    def test_clearBreadsUnavailableAtPickupLocation_keptChoiceWithinTheNewDaysLimit_keepsIt(
        self,
    ):
        bread = self._bread(max_pieces=3)
        self._choice(bread)
        self._choice(bread)
        mover = self._choice(bread)

        self._recheck(mover)

        self.assertEqual(mover.bread_id, bread.id)
