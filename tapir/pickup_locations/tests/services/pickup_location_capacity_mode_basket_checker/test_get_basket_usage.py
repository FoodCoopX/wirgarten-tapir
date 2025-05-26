from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetBasketUsage(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_BASKET_SIZES).update(
            value="small;medium"
        )
        cls.product_s = ProductFactory(name="S")
        cls.product_m = ProductFactory(name="M")
        cls.product_l = ProductFactory(name="L")
        ProductBasketSizeEquivalence.objects.bulk_create(
            [
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=cls.product_s, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=cls.product_s, quantity=0
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=cls.product_m, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=cls.product_l, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=cls.product_l, quantity=1
                ),
            ]
        )

    def test_getBasketUsage_default_returnsCorrectValues(self):
        self.assertEqual(
            1,
            PickupLocationCapacityModeBasketChecker.get_basket_size_usage(
                {}, self.product_s.id, "small"
            ),
        )
        self.assertEqual(
            0,
            PickupLocationCapacityModeBasketChecker.get_basket_size_usage(
                {}, self.product_s.id, "medium"
            ),
        )
        self.assertEqual(
            0,
            PickupLocationCapacityModeBasketChecker.get_basket_size_usage(
                {}, self.product_m.id, "small"
            ),
        )
        self.assertEqual(
            1,
            PickupLocationCapacityModeBasketChecker.get_basket_size_usage(
                {}, self.product_m.id, "medium"
            ),
        )
        self.assertEqual(
            1,
            PickupLocationCapacityModeBasketChecker.get_basket_size_usage(
                {}, self.product_l.id, "small"
            ),
        )
        self.assertEqual(
            1,
            PickupLocationCapacityModeBasketChecker.get_basket_size_usage(
                {}, self.product_l.id, "medium"
            ),
        )

    def test_getBasketUsage_someProductsAreMissingTheEquivalenceObject_defaultsToZero(
        self,
    ):
        self.assertEqual(
            0,
            PickupLocationCapacityModeBasketChecker.get_basket_size_usage(
                {}, self.product_m.id, "small"
            ),
        )
