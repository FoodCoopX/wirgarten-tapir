from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetProductSolidarityMinimum(TapirUnitTest):
    def test_getProductSolidarityMinimum_noProductHasChoices_returnsNone(self):
        result = SolidarityValidator.get_product_solidarity_minimum(
            [ProductFactory.build(solidarity_choices="")]
        )

        self.assertIsNone(result)

    def test_getProductSolidarityMinimum_productsHaveChoices_returnsSmallestChoice(
        self,
    ):
        result = SolidarityValidator.get_product_solidarity_minimum(
            [
                ProductFactory.build(solidarity_choices="5,10"),
                ProductFactory.build(solidarity_choices="-3,8"),
            ]
        )

        self.assertEqual(-3, result)
