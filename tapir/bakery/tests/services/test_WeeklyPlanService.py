import datetime

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    BreadSpecificsPerDeliveryDay,
)
from tapir.bakery.services.weekly_plan_service import (
    DeliveryDayIsOver,
    WeeklyPlanService,
)
from tapir.bakery.tests.factories import (
    AvailableBreadsForDeliveryDayFactory,
    BreadDeliveryFactory,
    BreadFactory,
    BreadSpecificsPerDeliveryDayFactory,
)
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone

YEAR = 2026
FROZEN_DATE = datetime.date(2026, 3, 14)  # Saturday, week 11
SOURCE_WEEK = 10
TARGET_WEEK = 12


def bake(bread, week, day, year=YEAR):
    AvailableBreadsForDeliveryDayFactory.create(
        year=year, delivery_week=week, delivery_day=day, bread=bread
    )


def plan(week, year=YEAR):
    return set(
        AvailableBreadsForDeliveryDay.objects.filter(
            year=year, delivery_week=week
        ).values_list("delivery_day", "bread__name")
    )


class WeeklyPlanTestCase(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime.combine(FROZEN_DATE, datetime.time(12)))
        self.roggen = BreadFactory.create(name="Roggen")
        self.dinkel = BreadFactory.create(name="Dinkel")
        self.kuerbis = BreadFactory.create(name="Kürbis")

    def _choice(self, bread, week, day):
        return BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=week,
            pickup_location=create_pickup_location_with_opening_times(open_days=[day]),
            bread=bread,
        )


class TestSetBreadBaked(WeeklyPlanTestCase):
    def _set(self, bread, is_baked, dry_run=False, week=TARGET_WEEK, day=4):
        return WeeklyPlanService.set_bread_baked(
            bread_id=bread.id,
            year=YEAR,
            delivery_week=week,
            delivery_day=day,
            is_baked=is_baked,
            cache={},
            dry_run=dry_run,
        )

    def test_switchingOn_bakesTheBread(self):
        result = self._set(self.roggen, is_baked=True)

        self.assertTrue(result.created)
        self.assertEqual(plan(TARGET_WEEK), {(4, "Roggen")})

    def test_switchingOff_clearsTheChoicesOfThatDay(self):
        bake(self.roggen, TARGET_WEEK, day=4)
        choice = self._choice(self.roggen, TARGET_WEEK, day=4)

        result = self._set(self.roggen, is_baked=False)

        self.assertTrue(result.deleted)
        self.assertEqual(result.cleared_choices, 1)
        self.assertEqual(plan(TARGET_WEEK), set())
        choice.refresh_from_db()
        self.assertIsNone(choice.bread_id)

    def test_dayThatIsOver_isRefused(self):
        # Tuesday of the frozen week 11 is over.
        bake(self.roggen, 11, day=1)

        for is_baked in (True, False):
            with self.subTest(is_baked=is_baked):
                with self.assertRaises(DeliveryDayIsOver):
                    self._set(
                        self.dinkel if is_baked else self.roggen,
                        is_baked,
                        week=11,
                        day=1,
                    )

        self.assertEqual(plan(11), {(1, "Roggen")})

    def test_switchingOff_dryRun_countsAndChangesNothing(self):
        bake(self.roggen, TARGET_WEEK, day=4)
        choice = self._choice(self.roggen, TARGET_WEEK, day=4)

        result = self._set(self.roggen, is_baked=False, dry_run=True)

        self.assertEqual(result.cleared_choices, 1)
        self.assertEqual(plan(TARGET_WEEK), {(4, "Roggen")})
        choice.refresh_from_db()
        self.assertEqual(choice.bread_id, self.roggen.id)


class TestCopyWeek(WeeklyPlanTestCase):
    def _copy(self, target_week=TARGET_WEEK, dry_run=False):
        return WeeklyPlanService.copy_week(
            source_year=YEAR,
            source_week=SOURCE_WEEK,
            target_year=YEAR,
            target_week=target_week,
            cache={},
            dry_run=dry_run,
        )

    def test_copy_replacesTheBreadsOfEachDay(self):
        bake(self.roggen, SOURCE_WEEK, day=1)
        bake(self.dinkel, SOURCE_WEEK, day=1)
        bake(self.roggen, SOURCE_WEEK, day=4)
        bake(self.kuerbis, TARGET_WEEK, day=1)
        bake(self.roggen, TARGET_WEEK, day=4)
        bake(self.dinkel, TARGET_WEEK, day=4)

        result = self._copy()

        self.assertEqual(
            plan(TARGET_WEEK), {(1, "Roggen"), (1, "Dinkel"), (4, "Roggen")}
        )
        self.assertEqual(result.copied_days, [1, 4])
        self.assertEqual(result.kept_days, [])
        self.assertEqual(
            plan(SOURCE_WEEK), {(1, "Roggen"), (1, "Dinkel"), (4, "Roggen")}
        )

    def test_copy_dayOnlyInTheTargetWeek_isEmptied(self):
        bake(self.roggen, SOURCE_WEEK, day=1)
        bake(self.dinkel, TARGET_WEEK, day=4)

        result = self._copy()

        self.assertEqual(plan(TARGET_WEEK), {(1, "Roggen")})
        self.assertEqual(result.copied_days, [1, 4])

    def test_copy_replacesTheDaySettings(self):
        bake(self.roggen, SOURCE_WEEK, day=1)
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR,
            delivery_week=SOURCE_WEEK,
            delivery_day=1,
            bread=self.roggen,
            min_pieces=5,
            max_pieces=20,
            min_remaining_pieces=2,
            fixed_pieces=None,
            max_direct_order_percent=50,
        )
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR,
            delivery_week=TARGET_WEEK,
            delivery_day=4,
            bread=self.dinkel,
            fixed_pieces=7,
        )

        self._copy()

        [specifics] = BreadSpecificsPerDeliveryDay.objects.filter(
            year=YEAR, delivery_week=TARGET_WEEK
        )
        self.assertEqual(
            (
                specifics.delivery_day,
                specifics.bread_id,
                specifics.min_pieces,
                specifics.max_pieces,
                specifics.min_remaining_pieces,
                specifics.fixed_pieces,
                specifics.max_direct_order_percent,
            ),
            (1, self.roggen.id, 5, 20, 2, None, 50),
        )
        self.assertEqual(
            BreadSpecificsPerDeliveryDay.objects.filter(
                year=YEAR, delivery_week=SOURCE_WEEK
            ).count(),
            1,
        )

    def test_copy_clearsChoicesOfBreadsNoLongerBakedThatDay(self):
        bake(self.roggen, SOURCE_WEEK, day=4)
        bake(self.roggen, TARGET_WEEK, day=4)
        bake(self.dinkel, TARGET_WEEK, day=4)
        kept = self._choice(self.roggen, TARGET_WEEK, day=4)
        cleared = self._choice(self.dinkel, TARGET_WEEK, day=4)

        result = self._copy()

        self.assertEqual(result.cleared_choices, 1)
        kept.refresh_from_db()
        cleared.refresh_from_db()
        self.assertEqual(kept.bread_id, self.roggen.id)
        self.assertIsNone(cleared.bread_id)

    def test_copy_dryRun_countsAndChangesNothing(self):
        bake(self.roggen, SOURCE_WEEK, day=4)
        bake(self.dinkel, TARGET_WEEK, day=4)
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR,
            delivery_week=TARGET_WEEK,
            delivery_day=4,
            bread=self.dinkel,
            fixed_pieces=7,
        )
        choice = self._choice(self.dinkel, TARGET_WEEK, day=4)

        result = self._copy(dry_run=True)

        self.assertEqual(result.copied_days, [4])
        self.assertEqual(result.cleared_choices, 1)
        self.assertEqual(plan(TARGET_WEEK), {(4, "Dinkel")})
        self.assertTrue(
            BreadSpecificsPerDeliveryDay.objects.filter(
                delivery_week=TARGET_WEEK
            ).exists()
        )
        choice.refresh_from_db()
        self.assertEqual(choice.bread_id, self.dinkel.id)

    def test_copy_daysThatAreOver_keepTheirSettings(self):
        # Week 11 is the frozen week: only Sunday (6) is still ahead, the
        # frozen Saturday (5) counts as over.
        bake(self.roggen, SOURCE_WEEK, day=1)
        bake(self.roggen, SOURCE_WEEK, day=5)
        bake(self.dinkel, SOURCE_WEEK, day=6)
        bake(self.kuerbis, 11, day=1)
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR, delivery_week=11, delivery_day=1, bread=self.kuerbis
        )
        choice = self._choice(self.kuerbis, 11, day=1)

        result = self._copy(target_week=11)

        self.assertEqual(result.copied_days, [6])
        self.assertEqual(result.kept_days, [1, 5])
        self.assertEqual(plan(11), {(1, "Kürbis"), (6, "Dinkel")})
        self.assertTrue(
            BreadSpecificsPerDeliveryDay.objects.filter(
                delivery_week=11, delivery_day=1
            ).exists()
        )
        choice.refresh_from_db()
        self.assertEqual(choice.bread_id, self.kuerbis.id)

    def test_copy_breadAlreadyBakedInTheTargetWeek_staysAsItIs(self):
        bake(self.roggen, SOURCE_WEEK, day=4)
        bake(self.roggen, TARGET_WEEK, day=4)
        entry = AvailableBreadsForDeliveryDay.objects.get(
            delivery_week=TARGET_WEEK, bread=self.roggen
        )

        self._copy()

        self.assertTrue(
            AvailableBreadsForDeliveryDay.objects.filter(pk=entry.pk).exists()
        )

    def test_copy_inactiveBreads_areLeftAlone(self):
        inactive = BreadFactory.create(name="Alt", is_active=False)
        bake(self.roggen, SOURCE_WEEK, day=4)
        bake(inactive, SOURCE_WEEK, day=4)
        bake(inactive, TARGET_WEEK, day=1)
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR,
            delivery_week=TARGET_WEEK,
            delivery_day=4,
            bread=inactive,
            max_pieces=3,
        )

        result = self._copy()

        self.assertEqual(result.copied_days, [4])
        self.assertEqual(plan(TARGET_WEEK), {(1, "Alt"), (4, "Roggen")})
        self.assertTrue(
            BreadSpecificsPerDeliveryDay.objects.filter(
                delivery_week=TARGET_WEEK, bread=inactive
            ).exists()
        )


class TestGetSourceWeeks(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getSourceWeeks_earlierWeeksWithActiveBreads_latestFirst(self):
        roggen = BreadFactory.create(name="Roggen")
        dinkel = BreadFactory.create(name="Dinkel")
        inactive = BreadFactory.create(name="Alt", is_active=False)
        bake(roggen, 52, day=1, year=2025)
        bake(roggen, 9, day=1)
        bake(roggen, 10, day=1)
        bake(roggen, 10, day=4)
        bake(dinkel, 10, day=4)
        bake(inactive, 11, day=1)
        bake(roggen, 12, day=1)
        bake(roggen, 13, day=1)

        sources = WeeklyPlanService.get_source_weeks(2026, 12, cache={})

        self.assertEqual(
            [(s.year, s.delivery_week, s.bread_count) for s in sources],
            [(2026, 10, 2), (2026, 9, 1), (2025, 52, 1)],
        )
