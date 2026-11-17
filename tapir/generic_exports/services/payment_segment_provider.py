import datetime

from django.db.models import QuerySet

from tapir.configuration.parameter import get_parameter_value
from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.generic_exports.services.payment_column_provider import PaymentColumnProvider
from tapir.payments.services.payment_export_exclusion_period_service import (
    PaymentExportExclusionPeriodService,
)
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys


class PaymentSegmentProvider:
    DESCRIPTION_ALL_PAYMENTS_THIS_MONTH = (
        "Alle in diesem Monat fälligen Zahlungen, "
        "egal ob für Genossenschaftsanteile oder Verträge."
    )

    @classmethod
    def get_payment_segments(cls):
        return [
            ExportSegment(
                id="payments.this_month",
                display_name="Alle Zahlungen für diesen Monat",
                get_queryset=cls.get_queryset_all_payments_this_month,
                get_available_columns=PaymentColumnProvider.get_payment_columns,
                get_description=cls.get_description_all_payments_this_month,
            ),
        ]

    @classmethod
    def get_description_all_payments_this_month(cls, cache: dict) -> str:
        if not get_parameter_value(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, cache=cache
        ):
            return cls.DESCRIPTION_ALL_PAYMENTS_THIS_MONTH
        return (
            f"{cls.DESCRIPTION_ALL_PAYMENTS_THIS_MONTH} Zahlungen von Mitgliedern, "
            "die vom Zahlungsexport ausgeschlossen sind, sind nicht enthalten."
        )

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
                PaymentExportExclusionPeriodService.build_payment_is_excluded_condition(
                    cache={}
                )
            )
            .select_related("mandate_ref", "mandate_ref__member")
        )
