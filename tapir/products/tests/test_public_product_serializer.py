from tapir.products.serializers import PublicProductSerializer
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import ProductPriceFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


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
