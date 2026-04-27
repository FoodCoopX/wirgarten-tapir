import datetime

from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.payments.monthly_sales_data import MonthlySalesData
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.payments.services.monthly_sales_column_provider import (
    MonthlySalesColumnProvider,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month


class MonthlySalesSegmentProvider:
    @classmethod
    def get_sales_segments(cls):
        return [
            ExportSegment(
                id="monthly_sales",
                display_name="Monatlicher Umsatz (vorheriger Monat)",
                description="Pro Produkt-Type",
                get_queryset=cls.get_list_monthly_sales_previous_month,
                get_available_columns=MonthlySalesColumnProvider.get_monthly_sales_columns,
            ),
        ]

    @classmethod
    def get_list_monthly_sales_previous_month(
        cls, reference_datetime: datetime.datetime
    ) -> list[MonthlySalesData]:
        cache = {}

        all_sales_data = []

        first_of_previous_month = (
            reference_datetime.date().replace(day=1) - datetime.timedelta(days=1)
        ).replace(day=1)
        end_of_previous_month = get_last_day_of_month(first_of_previous_month)
        subscriptions_by_product_type = TapirCache.get_subscriptions_by_product_type(
            cache=cache
        )

        for product_type in TapirCache.get_all_product_types(cache=cache):
            all_sales_data.append(
                MonthlySalesData(
                    contract_type_name=product_type.name,
                    sales=MonthPaymentBuilderSubscriptions.get_total_to_pay(
                        range_start=first_of_previous_month,
                        range_end=end_of_previous_month,
                        cache=cache,
                        contracts=subscriptions_by_product_type[product_type],
                    ),
                )
            )

        all_sales_data.append(
            MonthlySalesData(
                contract_type_name="Solidarbeitrag",
                sales=MonthPaymentBuilderSolidarityContributions.get_total_to_pay(
                    range_start=first_of_previous_month,
                    range_end=end_of_previous_month,
                    cache=cache,
                    contracts=list(
                        TapirCache.get_all_solidarity_contributions(cache=cache)
                    ),
                ),
            )
        )
        return all_sales_data
