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
from tapir.utils.services.test_data_generation.product_generator import (
    BREAD_PRODUCT_TYPE_NAME,
)
from tapir.utils.services.test_data_generation.user_generator import UserGenerator
from tapir.wirgarten.models import ProductType
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(UserGenerator, "get_user_count", return_value=25)
class TestGenerateAllWithBakery(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(ParameterKeys.MEMBER_BYPASS_KEYCLOAK, True)

    def test_generateAll_withBakery_producesACoherentWeek(self, _count):
        DataGenerator.generate_all(Organization.BAKERY)

        self.assertTrue(Bread.objects.exists())
        self.assertTrue(BreadDelivery.objects.exists())
        self.assertTrue(PreferredBread.objects.exists())
        self.assertTrue(BreadCapacityPickupLocation.objects.exists())
        self.assertTrue(AvailableBreadsForDeliveryDay.objects.exists())
        self.assertEqual(
            list(ProductType.objects.values_list("name", flat=True)),
            [BREAD_PRODUCT_TYPE_NAME],
        )

        year, week = BakeryGenerator.get_weeks_with_data()[0]
        grouped = BreadDeliveryContextService.get_deliveries_by_location_for_week(
            year=year, delivery_week=week, cache={}
        )
        self.assertTrue(grouped)

        # The bakery's stations open on Tuesday and Friday (0-based: 1 and 4).
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
        DataGenerator.generate_all(Organization.BAKERY)
        DataGenerator.clear()
        DataGenerator.generate_all(Organization.BAKERY)

        self.assertTrue(Bread.objects.exists())
