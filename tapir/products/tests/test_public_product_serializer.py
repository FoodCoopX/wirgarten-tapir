import datetime

from tapir.products.serializers import PublicProductSerializer
from tapir.wirgarten.models import Product
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import ProductPriceFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestPublicProductSerializer(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_solidarityChoices_valuesSet_returnsListOfFloats(self):
        product = ProductPriceFactory.create(
            product__solidarity_choices="-10, 0, 10"
        ).product

        data = PublicProductSerializer(instance=product, context={"cache": {}}).data

        self.assertEqual([-10.0, 0.0, 10.0], data["solidarity_choices"])

    def test_solidarityChoices_emptyValue_returnsEmptyList(self):
        product = ProductPriceFactory.create(product__solidarity_choices="").product

        data = PublicProductSerializer(instance=product, context={"cache": {}}).data

        self.assertEqual([], data["solidarity_choices"])

    def test_price_referenceDateInContext_returnsPriceAtReferenceDate(self):
        mock_timezone(self, now=datetime.datetime(year=2026, month=6, day=1))
        product = self._create_product_with_price_change()

        data = PublicProductSerializer(
            instance=product,
            context={
                "cache": {},
                "reference_date": datetime.date(year=2027, month=2, day=1),
            },
        ).data

        self.assertEqual(80, data["price"])

    def test_price_noReferenceDateInContext_returnsPriceAtToday(self):
        mock_timezone(self, now=datetime.datetime(year=2026, month=6, day=1))
        product = self._create_product_with_price_change()

        data = PublicProductSerializer(instance=product, context={"cache": {}}).data

        self.assertEqual(70, data["price"])

    @staticmethod
    def _create_product_with_price_change() -> Product:
        product = ProductPriceFactory.create(
            price=70, valid_from=datetime.date(year=2026, month=1, day=1)
        ).product
        ProductPriceFactory.create(
            product=product,
            price=80,
            valid_from=datetime.date(year=2027, month=1, day=1),
        )
        return product
