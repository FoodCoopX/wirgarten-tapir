from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestParseAmount(TapirUnitTest):
    def test_parseAmount_germanDecimal_returnsAmount(self):
        self.assertEqual(
            Decimal("150.50"),
            DataImportUtils.parse_amount({"Betrag": "150,50"}, "Betrag"),
        )

    def test_parseAmount_missingValue_returnsZero(self):
        self.assertEqual(Decimal("0"), DataImportUtils.parse_amount({}, "Betrag"))

    def test_parseAmount_invalidAmount_raisesError(self):
        for value in ("n/a", "-1", "1.234", "1000000", "NaN"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                DataImportUtils.parse_amount({"Betrag": value}, "Betrag")
