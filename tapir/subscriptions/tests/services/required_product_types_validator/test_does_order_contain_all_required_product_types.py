from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.required_product_types_validator import (
    RequiredProductTypesValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import ProductFactory, ProductTypeFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(TapirCache, "get_all_product_types", autospec=True, return_value=set())
class TestDoesOrderContainAllRequiredProductTypes(TapirUnitTest):
    def test_doesOrderContainAllRequiredProductTypes_orderIsEmpty_returnsTrue(
        self, mock_get_all_product_types: MagicMock
    ):
        mock_get_all_product_types.return_value = {
            ProductTypeFactory.build(must_be_subscribed_to=True)
        }

        self.assertTrue(
            RequiredProductTypesValidator.does_order_contain_all_required_product_types(
                order={}, cache={}
            )
        )

    def test_doesOrderContainAllRequiredProductTypes_requiredProductTypeMissing_returnsFalse(
        self, mock_get_all_product_types: MagicMock
    ):
        optional_product = ProductFactory.build(type__must_be_subscribed_to=False)
        mock_get_all_product_types.return_value = {
            ProductTypeFactory.build(must_be_subscribed_to=True),
            optional_product.type,
        }

        self.assertFalse(
            RequiredProductTypesValidator.does_order_contain_all_required_product_types(
                order={optional_product: 1}, cache={}
            )
        )

    def test_doesOrderContainAllRequiredProductTypes_requiredProductTypeOrdered_returnsTrue(
        self, mock_get_all_product_types: MagicMock
    ):
        required_product = ProductFactory.build(type__must_be_subscribed_to=True)
        optional_product = ProductFactory.build(type__must_be_subscribed_to=False)
        mock_get_all_product_types.return_value = {
            required_product.type,
            optional_product.type,
        }

        self.assertTrue(
            RequiredProductTypesValidator.does_order_contain_all_required_product_types(
                order={required_product: 1, optional_product: 1}, cache={}
            )
        )
