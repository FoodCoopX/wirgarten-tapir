import datetime

from tapir.wirgarten.models import ProductPrice
from tapir.wirgarten.service.products import (
    get_cheapest_product_price,
)
from tapir.wirgarten.tests.factories import (
    ProductPriceFactory,
    ProductFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak


class TapirGetFreeProductCapacity(TapirIntegrationTest):
    def setUp(self):
        set_bypass_keycloak()

    def test_getCheapestProductPrice_onlyOneProductPrice_ignoreStartDate(self):
        product_price: ProductPrice = ProductPriceFactory.create(
            price=100,
            valid_from=datetime.date(year=2023, month=12, day=31),
        )

        self.assertEqual(
            100,
            get_cheapest_product_price(
                product_price.product.type.id, datetime.date(year=2023, month=6, day=1)
            ),
        )

    def test_getCheapestProductPrice_hasOutdatedPrices_getNewestPrice(self):
        product = ProductFactory.create()

        ProductPriceFactory.create(
            product=product,
            price=100,
            valid_from=datetime.date(year=2023, month=12, day=31),
        )

        ProductPriceFactory.create(
            product=product,
            price=150,
            valid_from=datetime.date(year=2024, month=3, day=1),
        )

        self.assertEqual(
            150,
            get_cheapest_product_price(
                product.type.id, datetime.date(year=2024, month=3, day=2)
            ),
        )

    def test_getCheapestProductPrice_hasSeveralPrices_getCheapestPrice(self):
        product_type = ProductTypeFactory.create()
        product_s = ProductFactory.create(type=product_type)
        product_l = ProductFactory.create(type=product_type)

        ProductPriceFactory.create(
            product=product_s,
            price=100,
            valid_from=datetime.date(year=2024, month=1, day=1),
        )

        ProductPriceFactory.create(
            product=product_l,
            price=150,
            valid_from=datetime.date(year=2024, month=1, day=1),
        )

        self.assertEqual(
            100,
            get_cheapest_product_price(
                product_type.id, datetime.date(year=2024, month=1, day=1)
            ),
        )

    def test_getCheapestProductPrice_hasPriceStartingInTheFuture_ignoreFuturePrice(
        self,
    ):
        product = ProductFactory.create()

        ProductPriceFactory.create(
            product=product,
            price=150,
            valid_from=datetime.date(year=2023, month=12, day=31),
        )

        ProductPriceFactory.create(
            product=product,
            price=100,
            valid_from=datetime.date(year=2024, month=3, day=1),
        )

        self.assertEqual(
            150,
            get_cheapest_product_price(
                product.type.id, datetime.date(year=2024, month=2, day=1)
            ),
        )
