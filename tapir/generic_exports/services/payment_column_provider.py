from __future__ import annotations

import locale

from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.wirgarten.models import Payment
from tapir.wirgarten.utils import format_date


class PaymentColumnProvider:
    @classmethod
    def get_payment_columns(cls):
        return [
            ExportSegmentColumn(
                id="payment.member_full_name",
                display_name="Mitgliedsname",
                description="",
                get_value=cls.get_value_member_full_name,
            ),
            ExportSegmentColumn(
                id="payment.member_iban",
                display_name="IBAN",
                description="",
                get_value=cls.get_value_member_iban,
            ),
            ExportSegmentColumn(
                id="payment.amount",
                display_name="Betrag",
                description="",
                get_value=cls.get_value_amount,
            ),
            ExportSegmentColumn(
                id="payment.purpose",
                display_name="Verwendungszweck",
                description="",
                get_value=cls.get_value_purpose,
            ),
            ExportSegmentColumn(
                id="payment.mandate_ref",
                display_name="Mandatsreferenz",
                description="",
                get_value=cls.get_value_mandate_ref,
            ),
            ExportSegmentColumn(
                id="payment.mandate_date",
                display_name="Mandatsdatum",
                description="",
                get_value=cls.get_value_mandate_date,
            ),
        ]

    @classmethod
    def get_value_member_full_name(cls, payment: Payment, _, __):
        return payment.mandate_ref.member.get_display_name()

    @classmethod
    def get_value_member_iban(cls, payment: Payment, _, __):
        return payment.mandate_ref.member.iban

    @classmethod
    def get_value_amount(cls, payment: Payment, _, __):
        return locale.format_string("%.2f", payment.amount)

    @classmethod
    def get_value_purpose(cls, payment: Payment, _, __):
        type_name = payment.type
        if (
            type_name
            == MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION
        ):
            type_name = "Solidarbeitrag"

        return payment.mandate_ref.member.last_name + " " + type_name

    @classmethod
    def get_value_mandate_ref(cls, payment: Payment, _, __):
        return payment.mandate_ref.ref

    @classmethod
    def get_value_mandate_date(cls, payment: Payment, _, __):
        return format_date(payment.mandate_ref.member.sepa_consent)
