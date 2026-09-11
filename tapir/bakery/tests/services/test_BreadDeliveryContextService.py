import datetime

from django.db import connection
from django.test.utils import CaptureQueriesContext

from tapir.bakery.models import BreadDelivery
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.bakery.tests.factories import BreadDeliveryFactory, BreadSubscriptionFactory
from tapir.deliveries.models import Joker
from tapir.utils.shortcuts import week_to_monday
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak

YEAR = 2026
WEEK = 11  # Monday 2026-03-09


class TestBreadDeliveryContextService(TapirIntegrationTest):
    """
    pickup_location and joker_taken are derived rather than stored. This is the
    one place that derives them, so it is the one place that decides who ends
    up on the Abholliste.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        set_bypass_keycloak()

    @staticmethod
    def _create_delivery(pickup_location=None, member=None, week=WEEK, bread=None):
        subscription = BreadSubscriptionFactory.create(
            member=member or MemberFactory.create()
        )
        return BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=week,
            subscription=subscription,
            pickup_location=pickup_location,
            bread=bread,
        )

    @staticmethod
    def _reload(delivery):
        return BreadDelivery.objects.select_related("subscription__member").get(
            pk=delivery.pk
        )

    # ── reference date ────────────────────────────────────────────────

    def test_getReferenceDate_landsOnTheOrgDeliveryWeekdayOfThatWeek(self):
        reference_date = BreadDeliveryContextService.get_reference_date(
            YEAR, WEEK, cache={}
        )

        self.assertEqual(reference_date.isocalendar()[:2], (YEAR, WEEK))
        # The seeded org delivery weekday is Wednesday (2).
        self.assertEqual(reference_date, datetime.date(2026, 3, 11))

    def test_getReferenceDate_neverLeavesTheRequestedIsoWeek(self):
        # The joker lookup compares (ISO year, ISO week), so this is what makes
        # the choice of reference date safe.
        cache = {}
        for week in range(1, 54):
            reference_date = BreadDeliveryContextService.get_reference_date(
                2026, week, cache=cache
            )
            self.assertEqual(reference_date.isocalendar()[:2], (2026, week))

    # ── pickup location ───────────────────────────────────────────────

    def test_getPickupLocationId_memberRegisteredAtStation_returnsIt(self):
        pickup_location = PickupLocationFactory.create()
        delivery = self._create_delivery(pickup_location=pickup_location)

        self.assertEqual(
            BreadDeliveryContextService.get_pickup_location_id(
                self._reload(delivery), cache={}
            ),
            pickup_location.id,
        )

    def test_getPickupLocationId_memberWithNoStation_returnsNone(self):
        delivery = self._create_delivery()

        self.assertIsNone(
            BreadDeliveryContextService.get_pickup_location_id(
                self._reload(delivery), cache={}
            )
        )

    def test_getPickupLocationId_resolvesEachWeekAgainstValidFrom(self):
        old_location = PickupLocationFactory.create(name="Old")
        new_location = PickupLocationFactory.create(name="New")
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=old_location,
            valid_from=datetime.date(2025, 1, 1),
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=new_location,
            valid_from=week_to_monday(YEAR, WEEK + 1),
        )

        subscription = BreadSubscriptionFactory.create(member=member)
        before = BreadDeliveryFactory.create(
            year=YEAR, delivery_week=WEEK, subscription=subscription, bread=None
        )
        after = BreadDeliveryFactory.create(
            year=YEAR, delivery_week=WEEK + 1, subscription=subscription, bread=None
        )

        cache = {}
        self.assertEqual(
            BreadDeliveryContextService.get_pickup_location_id(
                self._reload(before), cache=cache
            ),
            old_location.id,
        )
        self.assertEqual(
            BreadDeliveryContextService.get_pickup_location_id(
                self._reload(after), cache=cache
            ),
            new_location.id,
        )

    # ── joker ─────────────────────────────────────────────────────────

    def test_isJokerTaken_jokerInThatWeek_isTrue(self):
        delivery = self._create_delivery(pickup_location=PickupLocationFactory.create())
        Joker.objects.create(
            member=delivery.subscription.member,
            # Any day of the week: the comparison is on (ISO year, ISO week).
            date=week_to_monday(YEAR, WEEK) + datetime.timedelta(days=3),
        )

        self.assertTrue(
            BreadDeliveryContextService.is_joker_taken(self._reload(delivery), cache={})
        )

    def test_isJokerTaken_jokerInAnotherWeek_isFalse(self):
        delivery = self._create_delivery(pickup_location=PickupLocationFactory.create())
        Joker.objects.create(
            member=delivery.subscription.member,
            date=week_to_monday(YEAR, WEEK + 1),
        )

        self.assertFalse(
            BreadDeliveryContextService.is_joker_taken(self._reload(delivery), cache={})
        )

    # ── grouping ──────────────────────────────────────────────────────

    def test_getDeliveriesByLocation_groupsByTheDerivedStation(self):
        first = PickupLocationFactory.create(name="Hofladen")
        second = PickupLocationFactory.create(name="Marktstand")
        at_first = self._create_delivery(pickup_location=first)
        at_second = [self._create_delivery(pickup_location=second) for _ in range(2)]

        grouped = BreadDeliveryContextService.get_deliveries_by_location_for_week(
            year=YEAR, delivery_week=WEEK, cache={}
        )

        self.assertEqual(set(grouped.keys()), {first.id, second.id})
        self.assertEqual([d.id for d in grouped[first.id]], [at_first.id])
        self.assertEqual(
            sorted(d.id for d in grouped[second.id]),
            sorted(d.id for d in at_second),
        )

    def test_getDeliveriesByLocation_memberWithNoStation_isDropped(self):
        self._create_delivery()

        self.assertEqual(
            BreadDeliveryContextService.get_deliveries_by_location_for_week(
                year=YEAR, delivery_week=WEEK, cache={}
            ),
            {},
        )

    def test_getDeliveriesByLocation_jokeredSlot_isDropped(self):
        # A jokered slot is not delivered, so it is on no list and counts
        # against no capacity.
        pickup_location = PickupLocationFactory.create()
        kept = self._create_delivery(pickup_location=pickup_location)
        jokered = self._create_delivery(pickup_location=pickup_location)
        Joker.objects.create(
            member=jokered.subscription.member, date=week_to_monday(YEAR, WEEK)
        )

        grouped = BreadDeliveryContextService.get_deliveries_by_location_for_week(
            year=YEAR, delivery_week=WEEK, cache={}
        )

        self.assertEqual([d.id for d in grouped[pickup_location.id]], [kept.id])

    def test_getDeliveriesByLocation_includeJokered_keepsThem(self):
        pickup_location = PickupLocationFactory.create()
        self._create_delivery(pickup_location=pickup_location)
        jokered = self._create_delivery(pickup_location=pickup_location)
        Joker.objects.create(
            member=jokered.subscription.member, date=week_to_monday(YEAR, WEEK)
        )

        grouped = BreadDeliveryContextService.get_deliveries_by_location_for_week(
            year=YEAR, delivery_week=WEEK, cache={}, include_jokered=True
        )

        self.assertEqual(len(grouped[pickup_location.id]), 2)

    def test_getDeliveriesForLocation_isTheSameDerivation(self):
        first = PickupLocationFactory.create()
        second = PickupLocationFactory.create()
        at_first = self._create_delivery(pickup_location=first)
        self._create_delivery(pickup_location=second)

        self.assertEqual(
            [
                d.id
                for d in BreadDeliveryContextService.get_deliveries_for_location_for_week(
                    year=YEAR,
                    delivery_week=WEEK,
                    pickup_location_id=first.id,
                    cache={},
                )
            ],
            [at_first.id],
        )

    def test_getDeliveriesForLocation_unknownStation_isEmpty(self):
        self._create_delivery(pickup_location=PickupLocationFactory.create())

        self.assertEqual(
            BreadDeliveryContextService.get_deliveries_for_location_for_week(
                year=YEAR,
                delivery_week=WEEK,
                pickup_location_id=PickupLocationFactory.create().id,
                cache={},
            ),
            [],
        )

    # ── cost ──────────────────────────────────────────────────────────

    def test_getDeliveriesByLocation_costDoesNotGrowWithTheNumberOfMembers(self):
        # The write path this replaced cost a few hundred queries per member.
        # Deriving has to stay flat, which is what the bulk joker accessor and
        # the shared pickup-location map are for.
        pickup_location = PickupLocationFactory.create()
        for _ in range(2):
            self._create_delivery(pickup_location=pickup_location)
        with CaptureQueriesContext(connection) as for_two:
            BreadDeliveryContextService.get_deliveries_by_location_for_week(
                year=YEAR, delivery_week=WEEK, cache={}
            )

        for _ in range(6):
            self._create_delivery(pickup_location=PickupLocationFactory.create())
        with CaptureQueriesContext(connection) as for_eight:
            grouped = BreadDeliveryContextService.get_deliveries_by_location_for_week(
                year=YEAR, delivery_week=WEEK, cache={}
            )

        self.assertEqual(sum(len(v) for v in grouped.values()), 8)
        self.assertEqual(len(for_eight), len(for_two))

    def test_getDeliveriesForLocation_sharedCache_groupsOnceForAllStations(self):
        # What pickup_lists_all_pdf relies on: rendering every station of a week
        # groups the deliveries once, not once per station.
        stations = [PickupLocationFactory.create() for _ in range(4)]
        for pickup_location in stations:
            self._create_delivery(pickup_location=pickup_location)

        cache = {}
        with CaptureQueriesContext(connection) as first:
            BreadDeliveryContextService.get_deliveries_for_location_for_week(
                year=YEAR,
                delivery_week=WEEK,
                pickup_location_id=stations[0].id,
                cache=cache,
            )
        self.assertGreater(len(first), 0)

        with CaptureQueriesContext(connection) as rest:
            for pickup_location in stations[1:]:
                BreadDeliveryContextService.get_deliveries_for_location_for_week(
                    year=YEAR,
                    delivery_week=WEEK,
                    pickup_location_id=pickup_location.id,
                    cache=cache,
                )

        self.assertEqual(len(rest), 0)
