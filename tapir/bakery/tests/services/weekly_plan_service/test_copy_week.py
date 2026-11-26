from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    BreadSpecificsPerDeliveryDay,
)
from tapir.bakery.services.weekly_plan_service import WeeklyPlanService
from tapir.bakery.tests.factories import (
    BreadFactory,
    BreadSpecificsPerDeliveryDayFactory,
)
from tapir.bakery.tests.services.weekly_plan_service.weekly_plan_service_test_case import (
    SOURCE_WEEK,
    TARGET_WEEK,
    YEAR,
    WeeklyPlanServiceTestCase,
    bake,
    plan,
)


class TestCopyWeek(WeeklyPlanServiceTestCase):
    def _copy(self, target_week=TARGET_WEEK, dry_run=False):
        return WeeklyPlanService.copy_week(
            source_year=YEAR,
            source_week=SOURCE_WEEK,
            target_year=YEAR,
            target_week=target_week,
            cache={},
            dry_run=dry_run,
        )

    def test_copyWeek_default_replacesTheBreadsOfEachDay(self):
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

    def test_copyWeek_dayOnlyInTheTargetWeek_emptiesTheDay(self):
        bake(self.roggen, SOURCE_WEEK, day=1)
        bake(self.dinkel, TARGET_WEEK, day=4)

        result = self._copy()

        self.assertEqual(plan(TARGET_WEEK), {(1, "Roggen")})
        self.assertEqual(result.copied_days, [1, 4])

    def test_copyWeek_default_replacesTheDaySettings(self):
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

    def test_copyWeek_breadNoLongerBakedThatDay_clearsItsChoices(self):
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

    def test_copyWeek_dryRun_countsAndChangesNothing(self):
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

    def test_copyWeek_daysThatAreOver_keepTheirSettings(self):
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

    def test_copyWeek_breadAlreadyBakedInTheTargetWeek_keepsItsEntry(self):
        bake(self.roggen, SOURCE_WEEK, day=4)
        bake(self.roggen, TARGET_WEEK, day=4)
        entry = AvailableBreadsForDeliveryDay.objects.get(
            delivery_week=TARGET_WEEK, bread=self.roggen
        )

        self._copy()

        self.assertTrue(
            AvailableBreadsForDeliveryDay.objects.filter(pk=entry.pk).exists()
        )

    def test_copyWeek_inactiveBreads_leavesThemAlone(self):
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
