from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.subscriptions.services.product_cancellation_data_builder import (
    ProductCancellationDataBuilder,
)
from tapir.wirgarten.tests.factories import ProductFactory


class TestProductCancellationDataBuilderBuildDataForAllProducts(SimpleTestCase):
    maxDiff = 2000

    @patch.object(
        ProductCancellationDataBuilder, "build_data_for_a_single_product", autospec=True
    )
    @patch.object(
        ProductCancellationDataBuilder, "get_subscribed_products", autospec=True
    )
    def test_buildDataForAllProducts_default_returnsListOfBuiltProducts(
        self,
        mock_get_subscribed_products: Mock,
        mock_build_data_for_a_single_product: Mock,
    ):
        products = ProductFactory.build_batch(size=3)
        mock_get_subscribed_products.return_value = products

        product_1, product_2, product_3 = products
        built_data_1 = Mock()
        built_data_2 = Mock()
        built_data_3 = Mock()
        built_datas = {
            product_1: built_data_1,
            product_2: built_data_2,
            product_3: built_data_3,
        }

        mock_build_data_for_a_single_product.side_effect = lambda **kwargs: built_datas[
            kwargs["product"]
        ]

        member = Mock()
        cache = Mock()

        result = ProductCancellationDataBuilder.build_data_for_all_products(
            member=member, cache=cache
        )

        self.assertEqual(set(built_datas.values()), set(result))

        mock_get_subscribed_products.assert_called_once_with(member=member, cache=cache)
        self.assertEqual(3, mock_build_data_for_a_single_product.call_count)
        mock_build_data_for_a_single_product.assert_has_calls(
            [call(member=member, product=product, cache=cache) for product in products],
            any_order=True,
        )
