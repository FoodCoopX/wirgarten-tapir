from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestParseSolidarityChoices(TapirUnitTest):
    def test_parseSolidarityChoices_emptyString_returnsEmptyList(self):
        self.assertEqual([], SolidarityValidator.parse_solidarity_choices("  "))

    def test_parseSolidarityChoices_validValues_returnsFloats(self):
        self.assertEqual(
            [-10.5, 0, 10],
            SolidarityValidator.parse_solidarity_choices("-10.5, 0 ,10"),
        )

    def test_parseSolidarityChoices_nonFiniteValue_raisesValueError(self):
        for value in ["nan", "5,inf", "-inf"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    SolidarityValidator.parse_solidarity_choices(value)
