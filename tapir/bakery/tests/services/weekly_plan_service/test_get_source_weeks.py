from tapir.bakery.services.weekly_plan_service import WeeklyPlanService
from tapir.bakery.tests.factories import BreadFactory
from tapir.bakery.tests.services.weekly_plan_service.weekly_plan_service_test_case import (
    bake,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetSourceWeeks(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getSourceWeeks_default_returnsEarlierWeeksWithActiveBreadsLatestFirst(
        self,
    ):
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
