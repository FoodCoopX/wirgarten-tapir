import datetime

from tapir.bestell_wizard.services.products_over_capacity_for_order_provider import (
    ProductsOverCapacityForOrderProvider,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetProductIds(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getProductIds_default_returnsOrderedProductsWithoutEnoughFreeCapacity(
        self,
    ):
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2021, month=1, day=1)
        )
        product_too_much_ordered, product_enough_capacity, product_not_ordered = (
            ProductFactory.create_batch(size=3, capacity=10)
        )
        for product in [
            product_too_much_ordered,
            product_enough_capacity,
            product_not_ordered,
        ]:
            ProductPriceFactory.create(
                product=product, size=1, valid_from=growing_period.start_date
            )
            SubscriptionFactory.create(
                period=growing_period, product=product, quantity=8
            )

        result = ProductsOverCapacityForOrderProvider.get_product_ids(
            order={product_too_much_ordered: 3, product_enough_capacity: 2},
            contract_start_date=datetime.date(year=2021, month=3, day=15),
            cache={},
        )

        self.assertEqual([product_too_much_ordered.id], result)
