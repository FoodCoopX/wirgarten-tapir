import datetime

from tapir.bestell_wizard.services.products_without_free_capacity_provider import (
    ProductsWithoutFreeCapacityProvider,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    GrowingPeriodFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetProductIds(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getProductIds_default_returnProductsThatAreAtOrOverCapacity(
        self,
    ):
        all_products = ProductFactory.create_batch(size=3, capacity=10)
        product_at_capacity, product_over_capacity, product_with_free_capacity = (
            all_products
        )
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2021, month=1, day=1)
        )
        for product in all_products:
            ProductPriceFactory.create(
                product=product, size=1, valid_from=growing_period.start_date
            )

        SubscriptionFactory.create(
            period=growing_period, product=product_at_capacity, quantity=10
        )
        SubscriptionFactory.create(
            period=growing_period, product=product_over_capacity, quantity=11
        )
        SubscriptionFactory.create(
            period=growing_period, product=product_with_free_capacity, quantity=9
        )

        result = ProductsWithoutFreeCapacityProvider.get_product_ids(
            cache={}, contract_start_date=datetime.date(year=2021, month=3, day=19)
        )

        self.assertEqual(
            {product_over_capacity.id, product_at_capacity.id}, set(result)
        )
