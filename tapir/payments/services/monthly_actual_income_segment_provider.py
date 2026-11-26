import datetime

from django.db.models import Sum

from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.payments.dataclasses import MonthlyActualIncome
from tapir.payments.services.monthly_actual_income_column_provider import (
    MonthlyActualIncomeColumnProvider,
)
from tapir.wirgarten.models import Payment


class MonthlyActualIncomeSegmentProvider:
    SEGMENT_ID_MONTHLY_ACTUAL_INCOME = "monthly_actual_income"

    @classmethod
    def get_actual_income_segments(cls):
        return [
            ExportSegment(
                id="monthly_actual_income",
                display_name="Monatlicher eingezogene Zahlungen",
                description="Pro Quelle: Produktanteil, Solibeitrag, Liefergebühren...",
                get_queryset=cls.get_list_actual_income,
                get_available_columns=MonthlyActualIncomeColumnProvider.get_monthly_actual_income_columns,
            ),
        ]

    @classmethod
    def get_list_actual_income(
        cls, reference_datetime: datetime.datetime
    ) -> list[MonthlyActualIncome]:
        income_by_type = (
            Payment.objects.filter(
                transaction__month__year=reference_datetime.year,
                transaction__month__month=reference_datetime.month,
            )
            .values("type")
            .annotate(income=Sum("amount"))
            .order_by("type")
        )
        return [
            MonthlyActualIncome(source_name=row["type"], income=row["income"])
            for row in income_by_type
        ]
