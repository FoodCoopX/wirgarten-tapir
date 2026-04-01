import datetime

from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    ProductPriceFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCalculateCapacityUsedByTheOrderedProducts(TapirIntegrationTest):
    def test_calculateCapacityUsedByTheOrderedProducts_default_returnsCorrectValue(
        self,
    ):
        ParameterDefinitions().import_definitions(bulk_create=True)
        reference_date = datetime.date(2020, 1, 1)
        product_type = ProductTypeFactory.create()
        product_s = ProductFactory(name="S", type=product_type)
        product_m = ProductFactory(name="M", type=product_type)
        product_l = ProductFactory(name="L", type=product_type)
        ProductPriceFactory.create(
            product=product_s,
            size=2,
            valid_from=reference_date - datetime.timedelta(days=1),
        )
        ProductPriceFactory.create(
            product=product_m,
            size=3,
            valid_from=reference_date - datetime.timedelta(days=1),
        )
        ProductPriceFactory.create(
            product=product_l,
            size=5,
            valid_from=reference_date - datetime.timedelta(days=1),
        )

        ordered_product_to_quantity_map = {product_s: 2, product_m: 3, product_l: 4}

        self.assertEqual(
            33,
            PickupLocationCapacityModeShareChecker.calculate_capacity_used_by_the_ordered_products(
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                product_type=product_type,
                reference_date=reference_date,
                cache={},
            ),
        )
