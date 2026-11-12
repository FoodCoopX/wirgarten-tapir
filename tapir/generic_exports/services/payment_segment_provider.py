import datetime

from django.db.models import QuerySet

from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.generic_exports.services.payment_column_provider import PaymentColumnProvider
from tapir.wirgarten.models import Payment


class PaymentSegmentProvider:
    @classmethod
    def get_payment_segments(cls):
        return [
            ExportSegment(
                id="payments.this_month",
                display_name="Alle Zahlungen für diesen Monat",
                description="Alle Zahlungen, die in diesem Monat fällig sind.",
                get_queryset=cls.get_queryset_all_payments_this_month,
                get_available_columns=PaymentColumnProvider.get_payment_columns,
            ),
        ]

    @classmethod
    def get_queryset_all_payments_this_month(
        cls, reference_datetime: datetime.datetime
    ) -> QuerySet:
        return Payment.objects.filter(
            due_date__year=reference_datetime.year,
            due_date__month=reference_datetime.month,
        ).select_related("mandate_ref", "mandate_ref__member")
