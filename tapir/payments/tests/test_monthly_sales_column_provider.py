from decimal import Decimal
from unittest.mock import Mock

from django.test import SimpleTestCase

from tapir.payments.monthly_sales_data import MonthlySalesData
from tapir.payments.services.monthly_sales_column_provider import (
    MonthlySalesColumnProvider,
)


class TestMonthlySalesColumnProvider(SimpleTestCase):
    def test_getValueProductTypeName_default_returnsName(self):
        data = MonthlySalesData(sales=Mock(), contract_type_name="test name")

        result = MonthlySalesColumnProvider.get_value_product_type_name(
            data, None, None
        )

        self.assertEqual("test name", result)

    def test_getValueSales_default_returnsFormattedSales(self):
        data = MonthlySalesData(sales=Decimal("12.345678"), contract_type_name=Mock())

        result = MonthlySalesColumnProvider.get_value_sales(data, None, None)

        self.assertEqual("12,35", result)
