from django.apps import AppConfig

from tapir.generic_exports.services.export_segment_manager import ExportSegmentManager


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.payments"

    def ready(self) -> None:
        from tapir.payments.services.monthly_sales_segment_provider import (
            MonthlySalesSegmentProvider,
        )

        for segment in MonthlySalesSegmentProvider.get_sales_segments():
            ExportSegmentManager.register_segment(segment)
