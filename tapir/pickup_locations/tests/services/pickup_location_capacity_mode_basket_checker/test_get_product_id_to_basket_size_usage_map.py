from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetProductIdToBasketSizeUsageMap(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=Parameter.PICKING_BASKET_SIZES).update(
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

    def test_getProductIdToBasketSizeUsageMap_default_returnsCorrectMap(self):
        result = PickupLocationCapacityModeBasketChecker.get_product_id_to_basket_size_usage_map(
            "small"
        )
        self.assertEqual(
            {self.product_s.id: 1, self.product_m.id: 0, self.product_l.id: 1}, result
        )

    def test_getProductIdToBasketSizeUsageMap_theIsAnEquivalenceForANonExistingBasketSize_resultNotAffected(
        self,
    ):
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="big", product=self.product_l, quantity=1
        )

        result = PickupLocationCapacityModeBasketChecker.get_product_id_to_basket_size_usage_map(
            "small"
        )
        self.assertEqual(
            {self.product_s.id: 1, self.product_m.id: 0, self.product_l.id: 1}, result
        )

    def test_getProductIdToBasketSizeUsageMap_someProductsAreMissingTheEquivalenceObject_defaultsToZero(
        self,
    ):
        result = PickupLocationCapacityModeBasketChecker.get_product_id_to_basket_size_usage_map(
            "small"
        )
        self.assertEqual(0, result[self.product_m.id])
