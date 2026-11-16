import datetime

from django.db.models import QuerySet, Exists, OuterRef, Q

from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.generic_exports.services.payment_column_provider import PaymentColumnProvider
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.models import PaymentExportExclusionPeriod
from tapir.wirgarten.models import Payment


class PaymentSegmentProvider:
    @classmethod
    def get_payment_segments(cls):
        return [
            ExportSegment(
                id="payments.this_month",
                display_name="Alle Zahlungen für diese Monat",
                description="Alle Zahlungen in diesem Monat fällig, "
                "egal ob von Geno-Anteile oder Produkt-Anteile",
                get_queryset=cls.get_queryset_all_payments_this_month,
                get_available_columns=PaymentColumnProvider.get_payment_columns,
            ),
        ]

    @classmethod
    def get_queryset_all_payments_this_month(
        cls, reference_datetime: datetime.datetime
    ) -> QuerySet:
        return (
            Payment.objects.filter(
                due_date__year=reference_datetime.year,
                due_date__month=reference_datetime.month,
            )
            .exclude(
                cls._build_member_is_excluded_from_export_condition(),
                ~Q(type=PAYMENT_TYPE_COOP_SHARES),
            )
            .select_related("mandate_ref", "mandate_ref__member")
        )

    @staticmethod
    def _build_member_is_excluded_from_export_condition() -> Exists:
        return Exists(
            PaymentExportExclusionPeriod.objects.filter(
                Q(end_date__isnull=True) | Q(end_date__gte=OuterRef("due_date")),
                member_id=OuterRef("mandate_ref__member_id"),
                start_date__lte=OuterRef("due_date"),
            )
        )
