import datetime

from tapir.bakery.models import AvailableBreadsForDeliveryDay
from tapir.bakery.tests.factories import (
    AvailableBreadsForDeliveryDayFactory,
    BreadDeliveryFactory,
    BreadFactory,
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


class WeeklyPlanServiceTestCase(TapirIntegrationTest):
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
