import datetime

from tapir.products.serializers import PublicProductTypeSerializer
from tapir.wirgarten.models import TaxRate
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import ProductTypeFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestPublicProductTypeSerializer(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, now=datetime.datetime(year=2026, month=6, day=1))
        self.product_type = ProductTypeFactory.create()
        TaxRate.objects.create(
            product_type=self.product_type,
            tax_rate=0.07,
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        TaxRate.objects.create(
            product_type=self.product_type,
            tax_rate=0.19,
            valid_from=datetime.date(year=2027, month=1, day=1),
        )

    def test_taxRate_referenceDateInContext_returnsTaxRateAtReferenceDate(self):
        data = PublicProductTypeSerializer(
            instance=self.product_type,
            context={
                "cache": {},
                "reference_date": datetime.date(year=2027, month=2, day=1),
            },
        ).data

        self.assertEqual(0.19, data["tax_rate"])

    def test_taxRate_noReferenceDateInContext_returnsTaxRateAtToday(self):
        data = PublicProductTypeSerializer(
            instance=self.product_type, context={"cache": {}}
        ).data

        self.assertEqual(0.07, data["tax_rate"])
