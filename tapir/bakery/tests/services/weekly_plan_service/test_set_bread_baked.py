from tapir.bakery.services.weekly_plan_service import WeeklyPlanService
from tapir.bakery.tests.services.weekly_plan_service.weekly_plan_service_test_case import (
    TARGET_WEEK,
    YEAR,
    WeeklyPlanServiceTestCase,
    bake,
    plan,
)


class TestSetBreadBaked(WeeklyPlanServiceTestCase):
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

    def test_setBreadBaked_switchedOn_bakesTheBread(self):
        result = self._set(self.roggen, is_baked=True)

        self.assertTrue(result.created)
        self.assertEqual(plan(TARGET_WEEK), {(4, "Roggen")})

    def test_setBreadBaked_switchedOff_clearsTheChoicesOfThatDay(self):
        bake(self.roggen, TARGET_WEEK, day=4)
        choice = self._choice(self.roggen, TARGET_WEEK, day=4)

        result = self._set(self.roggen, is_baked=False)

        self.assertTrue(result.deleted)
        self.assertEqual(result.cleared_choices, 1)
        self.assertEqual(plan(TARGET_WEEK), set())
        choice.refresh_from_db()
        self.assertIsNone(choice.bread_id)

    def test_setBreadBaked_switchedOffAsDryRun_countsAndChangesNothing(self):
        bake(self.roggen, TARGET_WEEK, day=4)
        choice = self._choice(self.roggen, TARGET_WEEK, day=4)

        result = self._set(self.roggen, is_baked=False, dry_run=True)

        self.assertEqual(result.cleared_choices, 1)
        self.assertEqual(plan(TARGET_WEEK), {(4, "Roggen")})
        choice.refresh_from_db()
        self.assertEqual(choice.bread_id, self.roggen.id)
