from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.wirgarten.tests.factories import ProductFactory, ProductPriceFactory


class TestCalculateGlobalCapacityUsedByTheOrderedProducts(SimpleTestCase):
    @patch(
        "tapir.subscriptions.services.global_capacity_checker.get_product_price",
        autospec=True,
    )
    def test_calculateGlobalCapacityUsedByTheOrderedProducts_default_returnsCorrectCapacity(
        self, mock_get_product_price: Mock
    ):
        product_1 = ProductFactory.build()
        product_2 = ProductFactory.build()
        product_3 = ProductFactory.build()
        product_prices = {
            product_1: ProductPriceFactory.build(product=product_1, size=1.25),
            product_2: ProductPriceFactory.build(product=product_2, size=2.33),
            product_3: ProductPriceFactory.build(product=product_3, size=3.44),
        }
        mock_get_product_price.side_effect = (
            lambda product, reference_date, cache: product_prices[product]
        )
        reference_date = Mock()
        cache = Mock()

        result = GlobalCapacityChecker.calculate_global_capacity_used_by_the_ordered_products(
            order_for_a_single_product_type={product_1: 1, product_2: 2, product_3: 3},
            reference_date=reference_date,
            cache=cache,
        )

        self.assertEqual(1 * 1.25 + 2 * 2.33 + 3 * 3.44, result)

        self.assertEqual(3, mock_get_product_price.call_count)
        mock_get_product_price.assert_has_calls(
            [
                call(product=product, reference_date=reference_date, cache=cache)
                for product in [product_1, product_2, product_3]
            ],
            any_order=True,
        )
