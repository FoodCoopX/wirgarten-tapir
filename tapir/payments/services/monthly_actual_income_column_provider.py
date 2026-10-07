from __future__ import annotations

from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.payments.dataclasses import MonthlyActualIncome
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.payments.services.month_payment_builder_delivery_charges import (
    MonthPaymentBuilderDeliveryCharges,
)
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.wirgarten.utils import format_currency


class MonthlyActualIncomeColumnProvider:
    COLUMN_ID_SOURCE_NAME = "monthly_actual_income_source_name"
    COLUMN_ID_INCOME = "monthly_actual_income_income"

    @classmethod
    def get_monthly_actual_income_columns(cls):
        return [
            ExportSegmentColumn(
                id=cls.COLUMN_ID_SOURCE_NAME,
                display_name="Quelle",
                description="",
                get_value=cls.get_value_source_name,
            ),
            ExportSegmentColumn(
                id=cls.COLUMN_ID_INCOME,
                display_name="Eingezogen",
                description="",
                get_value=cls.get_value_income,
            ),
        ]

    @classmethod
    def get_value_source_name(cls, data: MonthlyActualIncome, _, __):
        if (
            data.source_name
            == MonthPaymentBuilderDeliveryCharges.PAYMENT_TYPE_DELIVERY_CHARGE
        ):
            return "Liefergebühr"
        if (
            data.source_name
            == MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION
        ):
            return "Solidarbeitrag"
        if (
            data.source_name
            == MonthPaymentBuilderAssociationMembership.PAYMENT_TYPE_ASSOCIATION_MEMBERSHIP
        ):
            return "Vereinsmitgliedschaften"

        return data.source_name

    @classmethod
    def get_value_income(cls, data: MonthlyActualIncome, _, __):
        return format_currency(data.income)
