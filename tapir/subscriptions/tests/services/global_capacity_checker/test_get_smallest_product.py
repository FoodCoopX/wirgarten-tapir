from unittest.mock import patch, Mock, call

from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import (
    ProductPriceFactory,
    ProductTypeFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetSmallestProduct(TapirUnitTest):
    @patch(
        "tapir.subscriptions.services.global_capacity_checker.get_product_price",
        autospec=True,
    )
    @patch.object(TapirCache, "get_products_with_product_type", autospec=True)
    def test_getSmallestProduct_severalProducts_returnsSmallestProduct(
        self, mock_get_products_with_product_type: Mock, mock_get_product_price: Mock
    ):
        product_type = ProductTypeFactory.build()
        products = ProductFactory.build_batch(size=3, type=product_type)
        product_to_price_object = {
            product: ProductPriceFactory.build(product=product) for product in products
        }

        product_to_price_object[products[0]].size = 1
        product_to_price_object[products[1]].size = 0.5
        product_to_price_object[products[2]].size = 2

        reference_date = Mock()
        cache = Mock()

        mock_get_products_with_product_type.return_value = products
        mock_get_product_price.side_effect = (
            lambda product, **_: product_to_price_object[product]
        )

        result = GlobalCapacityChecker.get_smallest_product(
            product_type, reference_date=reference_date, cache=cache
        )

        self.assertEqual(products[1], result)

        mock_get_products_with_product_type.assert_called_once_with(
            cache=cache, product_type_id=product_type.id
        )
        self.assertEqual(3, mock_get_product_price.call_count)
        mock_get_product_price.assert_has_calls(
            [
                call(product=product, reference_date=reference_date, cache=cache)
                for product in products
            ],
            any_order=True,
        )

    @patch(
        "tapir.subscriptions.services.global_capacity_checker.get_product_price",
        autospec=True,
    )
    @patch.object(TapirCache, "get_products_with_product_type", autospec=True)
    def test_getSmallestProduct_onlyOneProduct_returnsSmallestProduct(
        self, mock_get_products_with_product_type: Mock, mock_get_product_price: Mock
    ):
        product_type = ProductTypeFactory.build()
        product = ProductFactory.build(type=product_type)
        product_price_object = ProductPriceFactory.build(product=product, size=3.44)

        reference_date = Mock()
        cache = Mock()

        mock_get_products_with_product_type.return_value = [product]
        mock_get_product_price.return_value = product_price_object

        result = GlobalCapacityChecker.get_smallest_product(
            product_type, reference_date=reference_date, cache=cache
        )

        self.assertEqual(product, result)

        mock_get_products_with_product_type.assert_called_once_with(
            cache=cache, product_type_id=product_type.id
        )
        mock_get_product_price.assert_called_once_with(
            product=product, reference_date=reference_date, cache=cache
        )

    @patch(
        "tapir.subscriptions.services.global_capacity_checker.get_product_price",
        autospec=True,
    )
    @patch.object(TapirCache, "get_products_with_product_type", autospec=True)
    def test_getSmallestProduct_noProducts_raisesError(
        self, mock_get_products_with_product_type: Mock, mock_get_product_price: Mock
    ):
        product_type = ProductTypeFactory.build(name="test product")

        reference_date = Mock()
        cache = Mock()

        mock_get_products_with_product_type.return_value = []

        with self.assertRaises(TapirImproperlyConfigured) as error_context:
            GlobalCapacityChecker.get_smallest_product(
                product_type, reference_date=reference_date, cache=cache
            )

        self.assertEqual(
            "No product found for product type test product (no_delivery)",
            str(error_context.exception),
        )
        mock_get_products_with_product_type.assert_called_once_with(
            cache=cache, product_type_id=product_type.id
        )
        mock_get_product_price.assert_not_called()
