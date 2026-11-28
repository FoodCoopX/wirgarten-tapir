from django.core.exceptions import ValidationError

from tapir.products.services.product_name_validator import ProductNameValidator
from tapir.wirgarten.models import Product
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateNameIsUnique(TapirUnitTest):
    @staticmethod
    def _build_cache(products: list[Product]) -> dict:
        return {"all_products": set(products)}

    def test_validateNameIsUnique_otherProductHasSameName_raisesError(self):
        cache = self._build_cache([ProductFactory.build(name="M-Ernteanteil")])

        with self.assertRaisesMessage(
            ValidationError,
            "Es gibt bereits ein Produkt mit dem Namen „M-Ernteanteil“.",
        ):
            ProductNameValidator.validate_name_is_unique(
                product_name="M-Ernteanteil", product_id=None, cache=cache
            )

    def test_validateNameIsUnique_sameNameIsTheEditedProduct_doesNothing(self):
        product = ProductFactory.build(name="M-Ernteanteil")
        cache = self._build_cache([product])

        ProductNameValidator.validate_name_is_unique(
            product_name="M-Ernteanteil", product_id=product.id, cache=cache
        )

    def test_validateNameIsUnique_sameNameIsADeletedProduct_doesNothing(self):
        cache = self._build_cache(
            [ProductFactory.build(name="M-Ernteanteil", deleted=True)]
        )

        ProductNameValidator.validate_name_is_unique(
            product_name="M-Ernteanteil", product_id=None, cache=cache
        )

    def test_validateNameIsUnique_noProductHasSameName_doesNothing(self):
        cache = self._build_cache([ProductFactory.build(name="L-Ernteanteil")])

        ProductNameValidator.validate_name_is_unique(
            product_name="M-Ernteanteil", product_id=None, cache=cache
        )
