import datetime
from decimal import Decimal

from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.payments.dataclasses import MonthlyActualIncome
from tapir.payments.services.monthly_actual_income_column_provider import (
    MonthlyActualIncomeColumnProvider,
)
from tapir.wirgarten.models import PaymentTransaction


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
        all_income_data = {}

        transactions = PaymentTransaction.objects.filter(
            month__year=reference_datetime.year, month__month=reference_datetime.month
        )
        payments = []
        for transaction in transactions:
            payments.extend(transaction.payment_set.all())

        for payment in payments:
            if payment.type not in all_income_data:
                all_income_data[payment.type] = MonthlyActualIncome(
                    source_name=payment.type, income=Decimal(0)
                )
            all_income_data[payment.type].income += payment.amount

        return list(all_income_data.values())
