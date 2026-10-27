from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetProductSolidarityChoices(TapirUnitTest):
    def test_getProductSolidarityChoices_severalProducts_returnsUnionWithoutDuplicates(
        self,
    ):
        products = [
            ProductFactory.build(solidarity_choices="-10, 0, 10"),
            ProductFactory.build(solidarity_choices=""),
            ProductFactory.build(solidarity_choices="-5,10,20"),
        ]

        result = SolidarityValidator.get_product_solidarity_choices(products)

        self.assertEqual({-10, 0, 10, -5, 20}, result)
