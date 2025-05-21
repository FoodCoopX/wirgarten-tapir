from __future__ import annotations

import datetime
import locale
from typing import TYPE_CHECKING, Dict

from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.service.products import get_current_growing_period

if TYPE_CHECKING:
    from tapir.wirgarten.models import Member


class MemberColumnProvider:
    @classmethod
    def get_member_columns(cls):
        return [
            ExportSegmentColumn(
                id="member_first_name",
                display_name="Vorname",
                description="",
                get_value=cls.get_value_member_first_name,
            ),
            ExportSegmentColumn(
                id="member_last_name",
                display_name="Nachname",
                description="",
                get_value=cls.get_value_member_last_name,
            ),
            ExportSegmentColumn(
                id="member_number",
                display_name="Mitgliedsnummer",
                description="",
                get_value=cls.get_value_member_number,
            ),
            ExportSegmentColumn(
                id="member_email_address",
                display_name="Mailadresse",
                description="",
                get_value=cls.get_value_member_email_address,
            ),
            ExportSegmentColumn(
                id="member_phone_number",
                display_name="Telefonnummer",
                description="",
                get_value=cls.get_value_member_phone_number,
            ),
            ExportSegmentColumn(
                id="member_iban",
                display_name="IBAN",
                description="",
                get_value=cls.get_value_member_iban,
            ),
            ExportSegmentColumn(
                id="member_account_owner",
                display_name="Name Kontoinhaber",
                description="",
                get_value=cls.get_value_member_account_owner,
            ),
            ExportSegmentColumn(
                id="member_joker_credit_value",
                display_name="Joker Gutschriftwert",
                description="der Gutschriftwert ermittelt sich aus = (hinterlegter Basisbetrag für Größe des "
                "Ernteanteils (ohne Solidarbeitrag!) / Anzahl der Lieferwochen) * Anzahl der genutzten Joker",
                get_value=cls.get_value_member_joker_credit_value,
            ),
            ExportSegmentColumn(
                id="member_joker_credit_intended_use",
                display_name="Joker Verwendungszweck",
                description="",
                get_value=cls.get_value_member_joker_credit_intended_use,
            ),
            ExportSegmentColumn(
                id="member_joker_credit_details",
                display_name="Joker Gutschrift Details",
                description="Gutschrift [Anzahl genutzte Joker] Joker in [Vertragsjahr]",
                get_value=cls.get_value_member_joker_credit_details,
            ),
        ]

    @classmethod
    def get_value_member_first_name(cls, member: Member, _, __):
        return member.first_name

    @classmethod
    def get_value_member_last_name(cls, member: Member, _, __):
        return member.last_name

    @classmethod
    def get_value_member_number(cls, member: Member, _, __):
        return str(member.member_no)

    @classmethod
    def get_value_member_email_address(cls, member: Member, _, __):
        return member.email

    @classmethod
    def get_value_member_phone_number(cls, member: Member, _, __):
        return member.phone_number

    @classmethod
    def get_value_member_iban(cls, member: Member, _, __):
        return member.iban

    @classmethod
    def get_value_member_account_owner(cls, member: Member, _, __):
        return member.account_owner

    @classmethod
    def get_value_member_joker_credit_value(
        cls, member: Member, reference_datetime: datetime.datetime, cache: Dict
    ):
        from tapir.deliveries.models import Joker

        growing_period = get_current_growing_period(
            reference_datetime.date(), cache=cache
        )
        jokers = Joker.objects.filter(
            date__gte=growing_period.start_date,
            date__lte=reference_datetime,
            member=member,
        )
        credit_value = sum(
            [
                DeliveryPriceCalculator.get_price_of_subscriptions_delivered_in_week(
                    member=member,
                    reference_date=joker.date,
                    only_subscriptions_affected_by_jokers=True,
                    cache=cache,
                )
                for joker in jokers
            ]
        )
        return locale.format_string("%.2f", credit_value)

    @classmethod
    def get_value_member_joker_credit_intended_use(cls, _, __, ___):
        return "Noch nicht implementiert, hängt von US 2.6. ab"

    @classmethod
    def get_value_member_joker_credit_details(
        cls, member: Member, reference_datetime: datetime.datetime, cache: Dict
    ):
        from tapir.deliveries.models import Joker

        growing_period = get_current_growing_period(
            reference_datetime.date(), cache=cache
        )
        nb_jokers = Joker.objects.filter(
            date__gte=growing_period.start_date,
            date__lte=reference_datetime,
            member=member,
        ).count()
        date_from = growing_period.start_date.strftime("%d.%m.%Y")
        date_to = reference_datetime.strftime("%d.%m.%Y")
        return f"Gutschrift {nb_jokers} genutzte Joker in Vertragsjahr {date_from}-{date_to}"
