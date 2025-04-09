import datetime

from tapir.wirgarten.models import ProductPrice
from tapir.wirgarten.service.products import (
    get_smallest_product_size,
)
from tapir.wirgarten.tests.factories import (
    ProductPriceFactory,
    ProductFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak


class TestGetFreeProductCapacity(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        set_bypass_keycloak()

    def test_getSmallestProductSize_onlyOneProductPrice_ignoreStartDate(self):
        product_price: ProductPrice = ProductPriceFactory.create(
            size=10,
            valid_from=datetime.date(year=2023, month=12, day=31),
        )

        self.assertEqual(
            10,
            get_smallest_product_size(
                product_price.product.type.id, datetime.date(year=2023, month=6, day=1)
            ),
        )

    def test_getSmallestProductSize_hasOutdatedPrices_getNewestPrice(self):
        product = ProductFactory.create()

        ProductPriceFactory.create(
            product=product,
            size=1,
            valid_from=datetime.date(year=2023, month=12, day=31),
        )

        ProductPriceFactory.create(
            product=product,
            size=1.5,
            valid_from=datetime.date(year=2024, month=3, day=1),
        )

        self.assertEqual(
            1.5,
            get_smallest_product_size(
                product.type.id, datetime.date(year=2024, month=3, day=2)
            ),
        )

    def test_getSmallestProductSize_hasSeveralPrices_getCheapestPrice(self):
        product_type = ProductTypeFactory.create()
        product_s = ProductFactory.create(type=product_type)
        product_l = ProductFactory.create(type=product_type)

        ProductPriceFactory.create(
            product=product_s,
            size=1,
            valid_from=datetime.date(year=2024, month=1, day=1),
        )

        ProductPriceFactory.create(
            product=product_l,
            size=1.5,
            valid_from=datetime.date(year=2024, month=1, day=1),
        )

        self.assertEqual(
            1,
            get_smallest_product_size(
                product_type.id, datetime.date(year=2024, month=1, day=1)
            ),
        )

    def test_getSmallestProductSize_hasPriceStartingInTheFuture_ignoreFuturePrice(
        self,
    ):
        product = ProductFactory.create()

        ProductPriceFactory.create(
            product=product,
            size=1.5,
            valid_from=datetime.date(year=2023, month=12, day=31),
        )

        ProductPriceFactory.create(
            product=product,
            size=1,
            valid_from=datetime.date(year=2024, month=3, day=1),
        )

        self.assertEqual(
            1.5,
            get_smallest_product_size(
                product.type.id, datetime.date(year=2024, month=2, day=1)
            ),
        )
