from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCalculateCapacityUsedByTheOrderedProducts(TapirIntegrationTest):
    def test_calculateCapacityUsedByTheOrderedProducts_default_returnsCorrectValue(
        self,
    ):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_BASKET_SIZES).update(
            value="small;medium"
        )
        product_s = ProductFactory(name="S")
        product_m = ProductFactory(name="M")
        product_l = ProductFactory(name="L")
        ProductBasketSizeEquivalence.objects.bulk_create(
            [
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=product_s, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=product_s, quantity=0
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=product_m, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=product_l, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=product_l, quantity=1
                ),
            ]
        )

        ordered_product_to_quantity_map = {product_s: 2, product_m: 3, product_l: 4}

        self.assertEqual(
            6,
            PickupLocationCapacityModeBasketChecker.calculate_capacity_used_by_the_ordered_products(
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                basket_size="small",
            ),
        )
        self.assertEqual(
            7,
            PickupLocationCapacityModeBasketChecker.calculate_capacity_used_by_the_ordered_products(
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                basket_size="medium",
            ),
        )
