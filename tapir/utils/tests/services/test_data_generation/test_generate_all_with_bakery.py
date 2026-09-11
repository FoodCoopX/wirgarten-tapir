from unittest.mock import patch

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    Bread,
    BreadCapacityPickupLocation,
    BreadDelivery,
    PreferredBread,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.bakery_generator import BakeryGenerator
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.utils.services.test_data_generation.user_generator import UserGenerator
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak


@patch.object(UserGenerator, "get_user_count", return_value=25)
class TestGenerateAllWithBakery(TapirIntegrationTest):
    """Runs the whole pipeline, which is where the ordering rules bite."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        set_bypass_keycloak()

    def test_generateAll_withBakery_producesACoherentWeek(self, _count):
        DataGenerator.generate_all(Organization.BAKERY)

        self.assertTrue(Bread.objects.exists())
        self.assertTrue(BreadDelivery.objects.exists())
        self.assertTrue(
            PreferredBread.objects.exists(),
            "without favourites the solver cannot be preference-aware",
        )
        self.assertTrue(BreadCapacityPickupLocation.objects.exists())
        self.assertTrue(AvailableBreadsForDeliveryDay.objects.exists())

        year, week = BakeryGenerator.get_weeks_with_data()[0]
        grouped = BreadDeliveryContextService.get_deliveries_by_location_for_week(
            year=year, delivery_week=week, cache={}
        )
        self.assertTrue(grouped, "the current week must land somewhere")

        # Both weekdays BIOTOP actually delivers on: Thursday for ten stations
        # and Monday for Biotop-Hofpunkt, which opens Monday morning. Hard
        # coding day 4 would hide every Hofpunkt delivery from the solver.
        self.assertEqual(
            set(
                AvailableBreadsForDeliveryDay.objects.values_list(
                    "delivery_day", flat=True
                )
            ),
            {1, 4},
        )

        cache = {}
        for delivery in BreadDelivery.objects.filter(
            year=year, delivery_week=week, bread__isnull=False
        ).select_related("subscription__member", "bread"):
            self.assertTrue(
                BreadCapacityPickupLocation.objects.filter(
                    year=delivery.year,
                    delivery_week=delivery.delivery_week,
                    bread=delivery.bread,
                    pickup_location_id=BreadDeliveryContextService.get_pickup_location_id(
                        delivery, cache=cache
                    ),
                ).exists()
            )

    def test_generateAll_twiceWithBakery_doesNotCollide(self, _count):
        # Bread.name is unique, so this only works because clear() removes the
        # bakery masterdata too.
        DataGenerator.generate_all(Organization.BAKERY)
        DataGenerator.clear()
        DataGenerator.generate_all(Organization.BAKERY)

        self.assertTrue(Bread.objects.exists())
