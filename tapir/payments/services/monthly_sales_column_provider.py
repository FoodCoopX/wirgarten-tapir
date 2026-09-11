from __future__ import annotations

from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.payments.monthly_sales_data import MonthlySalesData
from tapir.wirgarten.utils import format_currency


class MonthlySalesColumnProvider:
    @classmethod
    def get_monthly_sales_columns(cls):
        return [
            ExportSegmentColumn(
                id="monthly_sales_product_type_name",
                display_name="Produkttyp Name",
                description="",
                get_value=cls.get_value_product_type_name,
            ),
            ExportSegmentColumn(
                id="monthly_sales_product_type_sales",
                display_name="Umsatz",
                description="",
                get_value=cls.get_value_sales,
            ),
        ]

    @classmethod
    def get_value_product_type_name(cls, sales_data: MonthlySalesData, _, __):
        return sales_data.contract_type_name

    @classmethod
    def get_value_sales(cls, sales_data: MonthlySalesData, _, __):
        return format_currency(sales_data.sales)
