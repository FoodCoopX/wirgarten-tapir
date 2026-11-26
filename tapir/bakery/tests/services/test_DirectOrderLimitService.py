from tapir.bakery.services.direct_order_limit_service import (
    CAPACITY_SOURCE_BREAD_MAX,
    CAPACITY_SOURCE_DAY_MAX,
    CAPACITY_SOURCE_FIXED,
    CAPACITY_SOURCE_GROUP_MAX,
    DirectOrderLimitService,
)
from tapir.bakery.tests.factories import (
    BreadDeliveryFactory,
    BreadFactory,
    BreadGroupFactory,
    BreadSpecificsPerDeliveryDayFactory,
    offer_bread_at_pickup_location,
)
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

YEAR = 2026
WEEK = 11
DAY = 3


class TestDirectOrderLimitService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.location = create_pickup_location_with_opening_times([DAY])

    def _bread(self, name="Roggenbrot", **kwargs):
        kwargs.setdefault("min_remaining_pieces", 0)
        bread = BreadFactory.create(name=name, **kwargs)
        offer_bread_at_pickup_location(
            bread, self.location, year=YEAR, delivery_week=WEEK
        )
        return bread

    def _day_settings(self, bread, **kwargs):
        return BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread, **kwargs
        )

    def _order(self, bread, pickup_location=None, **kwargs):
        return BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pickup_location or self.location,
            bread=bread,
            **kwargs,
        )

    def _limits(self, **kwargs):
        return DirectOrderLimitService.get_limits_for_day(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, cache={}, **kwargs
        )

    def test_limit_isThePercentageOfTheCapacityLessMinRest(self):
        # The example of the user story: 80 % of 60 less 10 are 40.
        bread = self._bread(
            max_pieces=60, min_remaining_pieces=10, max_direct_order_percent=80
        )

        limit = self._limits().breads[bread.id]

        self.assertEqual(limit.total_capacity, 60)
        self.assertEqual(limit.total_capacity_source, CAPACITY_SOURCE_BREAD_MAX)
        self.assertEqual(limit.limit, 40)

    def test_limit_isRoundedDown(self):
        bread = self._bread(max_pieces=10, max_direct_order_percent=33)

        self.assertEqual(self._limits().breads[bread.id].limit, 3)

    def test_limit_withoutAnySetting_isEverythingButMinRest(self):
        bread = self._bread(max_pieces=20, min_remaining_pieces=5)

        self.assertEqual(self._limits().breads[bread.id].limit, 15)

    def test_limit_minRestAboveTheCapacity_isZero(self):
        bread = self._bread(max_pieces=5, min_remaining_pieces=8)

        self.assertEqual(self._limits().breads[bread.id].limit, 0)

    def test_limit_withoutMax_isUnlimited(self):
        bread = self._bread(max_pieces=None)
        self._order(bread)

        limits = self._limits()

        self.assertIsNone(limits.breads[bread.id].limit)
        self.assertIsNone(limits.remaining(bread.id))

    def test_limit_dayPercentageOverridesTheBreads(self):
        bread = self._bread(max_pieces=10, max_direct_order_percent=80)
        self._day_settings(bread, max_direct_order_percent=50)

        limit = self._limits().breads[bread.id]

        self.assertEqual(limit.percent, 50)
        self.assertEqual(limit.default_percent, 80)
        self.assertEqual(limit.limit, 5)

    def test_limit_dayMaxAndMinRestOverrideTheBreads(self):
        bread = self._bread(max_pieces=10, min_remaining_pieces=2)
        self._day_settings(bread, max_pieces=30, min_remaining_pieces=10)

        limit = self._limits().breads[bread.id]

        self.assertEqual(limit.total_capacity_source, CAPACITY_SOURCE_DAY_MAX)
        self.assertEqual(limit.limit, 20)

    def test_limit_fixedPiecesOverrideMax(self):
        bread = self._bread(max_pieces=10)
        self._day_settings(bread, max_pieces=30, fixed_pieces=12)

        limit = self._limits().breads[bread.id]

        self.assertEqual(limit.total_capacity, 12)
        self.assertEqual(limit.total_capacity_source, CAPACITY_SOURCE_FIXED)

    def test_limit_zeroOnTheDay_overridesTheBreadsValues(self):
        fixed_zero = self._bread(name="Brot A", max_pieces=10)
        self._day_settings(fixed_zero, fixed_pieces=0)
        percent_zero = self._bread(name="Brot B", max_pieces=10)
        self._day_settings(percent_zero, max_direct_order_percent=0)
        min_rest_zero = self._bread(
            name="Brot C", max_pieces=10, min_remaining_pieces=5
        )
        self._day_settings(min_rest_zero, min_remaining_pieces=0)

        limits = self._limits()

        self.assertEqual(limits.breads[fixed_zero.id].total_capacity, 0)
        self.assertEqual(limits.breads[fixed_zero.id].limit, 0)
        self.assertEqual(limits.breads[percent_zero.id].limit, 0)
        self.assertEqual(limits.breads[min_rest_zero.id].limit, 10)

    def test_remaining_moreOrdersThanTheLimit_isZero(self):
        # Orders made before the limit was lowered stay.
        bread = self._bread(max_pieces=10, max_direct_order_percent=20)
        for _ in range(3):
            self._order(bread)

        limits = self._limits()

        self.assertEqual(limits.breads[bread.id].ordered, 3)
        self.assertEqual(limits.remaining(bread.id), 0)

    def test_breads_notBakedThatDayOrInactive_areLeftOut(self):
        other_day = BreadFactory.create(name="Dinkelbrot")
        offer_bread_at_pickup_location(
            other_day,
            create_pickup_location_with_opening_times([DAY + 1]),
            year=YEAR,
            delivery_week=WEEK,
        )
        inactive = self._bread(name="Vollkornbrot", is_active=False)

        limits = self._limits()

        self.assertNotIn(other_day.id, limits.breads)
        self.assertNotIn(inactive.id, limits.breads)
        self.assertEqual(limits.remaining(inactive.id), 0)

    def test_ordered_countsAllStationsOfTheDayOnly(self):
        bread = self._bread(max_pieces=10)
        self._order(bread)
        self._order(bread, create_pickup_location_with_opening_times([DAY]))
        self._order(bread, create_pickup_location_with_opening_times([DAY + 1]))

        limits = self._limits()

        self.assertEqual(limits.breads[bread.id].ordered, 2)
        self.assertEqual(limits.remaining(bread.id), 8)

    def test_ordered_leavesOutJokeredSlotsAndTheExcludedDelivery(self):
        bread = self._bread(max_pieces=10)
        mine = self._order(bread)
        self._order(bread, joker_taken=True)

        limits = self._limits(exclude_delivery_ids=[mine.id])

        self.assertEqual(limits.breads[bread.id].ordered, 0)

    def test_group_breadsUseTheGroupMaxAndTheHighestPercentage(self):
        group = BreadGroupFactory.create(name="Teig1")
        bread_a = self._bread(
            name="Brot A", group=group, max_pieces=48, max_direct_order_percent=80
        )
        bread_b = self._bread(
            name="Brot B", group=group, max_pieces=60, max_direct_order_percent=60
        )

        limits = self._limits()

        self.assertEqual(limits.breads[bread_a.id].total_capacity, 48)
        self.assertEqual(
            limits.breads[bread_a.id].total_capacity_source, CAPACITY_SOURCE_GROUP_MAX
        )
        self.assertEqual(limits.breads[bread_a.id].limit, 38)
        self.assertEqual(limits.breads[bread_b.id].limit, 28)
        group_limit = limits.groups[group.id]
        self.assertEqual(group_limit.total_capacity, 48)
        self.assertEqual(group_limit.percent, 80)
        self.assertEqual(group_limit.limit, 38)

    def test_group_remainingIsTheSmallerOfTheBreadsAndTheGroups(self):
        group = BreadGroupFactory.create(name="Teig1")
        bread_a = self._bread(
            name="Brot A", group=group, max_pieces=48, max_direct_order_percent=80
        )
        bread_b = self._bread(
            name="Brot B", group=group, max_pieces=60, max_direct_order_percent=60
        )
        for _ in range(30):
            self._order(bread_a)

        limits = self._limits()

        # B alone could take 28, but the group has 38 - 30 left.
        self.assertEqual(limits.remaining(bread_b.id), 8)
        self.assertEqual(limits.remaining(bread_a.id), 8)

    def test_group_minRestOfAllItsBreadsIsSubtracted(self):
        group = BreadGroupFactory.create(name="Teig1")
        self._bread(name="Brot A", group=group, max_pieces=40, min_remaining_pieces=5)
        self._bread(name="Brot B", group=group, max_pieces=40, min_remaining_pieces=3)

        group_limit = self._limits().groups[group.id]

        self.assertEqual(group_limit.min_remaining, 8)
        self.assertEqual(group_limit.limit, 32)

    def test_group_breadWithDayMax_usesItButStillCountsTowardTheGroup(self):
        group = BreadGroupFactory.create(name="Teig1")
        bread_a = self._bread(name="Brot A", group=group, max_pieces=10)
        bread_b = self._bread(name="Brot B", group=group, max_pieces=10)
        self._day_settings(bread_a, max_pieces=4)
        for _ in range(4):
            self._order(bread_a)

        limits = self._limits()

        self.assertEqual(
            limits.breads[bread_a.id].total_capacity_source, CAPACITY_SOURCE_DAY_MAX
        )
        self.assertEqual(limits.remaining(bread_a.id), 0)
        self.assertEqual(limits.remaining(bread_b.id), 6)

    def test_group_dayPercentageAndMinRestOfItsBreadsCount(self):
        group = BreadGroupFactory.create(name="Teig1")
        bread_a = self._bread(
            name="Brot A", group=group, max_pieces=40, max_direct_order_percent=50
        )
        bread_b = self._bread(
            name="Brot B", group=group, max_pieces=40, max_direct_order_percent=50
        )
        self._day_settings(bread_a, max_direct_order_percent=75)
        self._day_settings(bread_b, min_remaining_pieces=8)

        group_limit = self._limits().groups[group.id]

        self.assertEqual(group_limit.percent, 75)
        self.assertEqual(group_limit.min_remaining, 8)
        self.assertEqual(group_limit.limit, 24)

    def test_group_breadWithFixedPieces_takesItsAmountOffTheGroup(self):
        group = BreadGroupFactory.create(name="Teig1")
        fixed = self._bread(name="Brot A", group=group, max_pieces=12)
        other = self._bread(name="Brot B", group=group, max_pieces=10)
        self._day_settings(fixed, fixed_pieces=4)

        limits = self._limits()

        # The solver bakes the 4 whether anyone orders them or not, and the
        # group's max of 10 covers them too, so 6 are left for Brot B.
        self.assertEqual(
            limits.breads[fixed.id].total_capacity_source, CAPACITY_SOURCE_FIXED
        )
        self.assertEqual(limits.remaining(fixed.id), 4)
        group_limit = limits.groups[group.id]
        self.assertEqual(group_limit.bread_ids, [other.id])
        self.assertEqual((group_limit.max_pieces, group_limit.fixed_pieces), (10, 4))
        self.assertEqual(group_limit.total_capacity, 6)
        self.assertEqual(limits.breads[other.id].total_capacity, 6)
        self.assertEqual(limits.remaining(other.id), 6)

    def test_group_ordersOfTheFixedBread_doNotCountAgainstTheOthers(self):
        group = BreadGroupFactory.create(name="Teig1")
        fixed = self._bread(name="Brot A", group=group, max_pieces=10)
        other = self._bread(name="Brot B", group=group, max_pieces=10)
        self._day_settings(fixed, fixed_pieces=6)
        for _ in range(6):
            self._order(fixed)

        limits = self._limits()

        self.assertEqual(limits.remaining(fixed.id), 0)
        self.assertEqual(limits.groups[group.id].ordered, 0)
        self.assertEqual(limits.remaining(other.id), 4)

    def test_group_breadWithFixedPieces_isNotBoundByTheGroupsLimit(self):
        # The group has 12 - 10 = 2 left for Brot B; Brot A's 10 are baked
        # anyway, so all of them stay orderable once B's 2 are taken.
        group = BreadGroupFactory.create(name="Teig1")
        fixed = self._bread(name="Brot A", group=group, max_pieces=12)
        other = self._bread(name="Brot B", group=group, max_pieces=12)
        self._day_settings(fixed, fixed_pieces=10)
        for _ in range(2):
            self._order(other)

        limits = self._limits()

        self.assertEqual(limits.remaining(other.id), 0)
        self.assertEqual(limits.remaining(fixed.id), 10)

    def test_group_dayMinimumOfAnotherBread_isHeldBack(self):
        # Brot A is baked at least 10 times, so of the group's 20 only 10
        # are left for Brot B, as in the solver.
        group = BreadGroupFactory.create(name="Teig1")
        bread_a = self._bread(name="Brot A", group=group, max_pieces=20)
        bread_b = self._bread(name="Brot B", group=group, max_pieces=20)
        self._day_settings(bread_a, min_pieces=10)

        limits = self._limits()

        self.assertEqual(limits.groups[group.id].open_min_pieces, 10)
        self.assertEqual(limits.remaining(bread_b.id), 10)

    def test_group_ordersWithinABreadsDayMinimum_takeNothingFromTheOthers(self):
        group = BreadGroupFactory.create(name="Teig1")
        bread_a = self._bread(name="Brot A", group=group, max_pieces=20)
        bread_b = self._bread(name="Brot B", group=group, max_pieces=20)
        self._day_settings(bread_a, min_pieces=10)
        for _ in range(4):
            self._order(bread_a)

        self.assertEqual(self._limits().remaining(bread_b.id), 10)

        for _ in range(8):
            self._order(bread_a)

        # 12 of A are past its minimum: 20 - 12 leaves 8 for B.
        limits = self._limits()
        self.assertEqual(limits.groups[group.id].open_min_pieces, 0)
        self.assertEqual(limits.remaining(bread_b.id), 8)

    def test_group_openDayMinimum_doesNotBlockItsOwnBread(self):
        # The 15 of Brot A are baked anyway, so members may order all of them
        # once Brot B has taken the rest of the group's 20.
        group = BreadGroupFactory.create(name="Teig1")
        bread_a = self._bread(name="Brot A", group=group, max_pieces=20)
        bread_b = self._bread(name="Brot B", group=group, max_pieces=20)
        self._day_settings(bread_a, min_pieces=15)
        for _ in range(5):
            self._order(bread_b)

        limits = self._limits()

        self.assertEqual(limits.remaining(bread_b.id), 0)
        self.assertEqual(limits.remaining(bread_a.id), 15)

    def test_group_onlyBreadsWithFixedPieces_hasNoGroupLimit(self):
        group = BreadGroupFactory.create(name="Teig1")
        bread_a = self._bread(name="Brot A", group=group, max_pieces=10)
        bread_b = self._bread(name="Brot B", group=group, max_pieces=10)
        self._day_settings(bread_a, fixed_pieces=3)
        self._day_settings(bread_b, fixed_pieces=5)

        limits = self._limits()

        self.assertEqual(limits.groups, {})
        self.assertEqual(limits.remaining(bread_b.id), 5)

    def test_group_breadAloneInItsGroupThatDay_usesItsOwnMax(self):
        group = BreadGroupFactory.create(name="Teig1")
        bread = self._bread(group=group, max_pieces=12)
        BreadFactory.create(name="Dinkelbrot", group=group, max_pieces=5)

        limits = self._limits()

        self.assertEqual(
            limits.breads[bread.id].total_capacity_source, CAPACITY_SOURCE_BREAD_MAX
        )
        self.assertEqual(limits.breads[bread.id].limit, 12)
        self.assertEqual(limits.groups, {})

    def test_group_withoutAnyMax_isUnlimited(self):
        group = BreadGroupFactory.create(name="Teig1")
        bread = self._bread(name="Brot A", group=group, max_pieces=None)
        self._bread(name="Brot B", group=group, max_pieces=None)

        limits = self._limits()

        self.assertIsNone(limits.groups[group.id].limit)
        self.assertIsNone(limits.remaining(bread.id))
