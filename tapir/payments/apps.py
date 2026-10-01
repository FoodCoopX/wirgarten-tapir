from django.apps import AppConfig

from tapir.generic_exports.services.export_segment_manager import ExportSegmentManager


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.payments"

    def ready(self) -> None:
        from tapir.payments.services.monthly_sales_segment_provider import (
            MonthlySalesSegmentProvider,
        )
        from tapir.payments.services.monthly_actual_income_segment_provider import (
            MonthlyActualIncomeSegmentProvider,
        )

        for segment in MonthlySalesSegmentProvider.get_sales_segments():
            ExportSegmentManager.register_segment(segment)
        for segment in MonthlyActualIncomeSegmentProvider.get_actual_income_segments():
            ExportSegmentManager.register_segment(segment)
