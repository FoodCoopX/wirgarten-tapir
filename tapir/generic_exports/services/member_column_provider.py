from __future__ import annotations

import datetime
import locale
from typing import TYPE_CHECKING, Dict

from django.db.models import (
    F,
    Max,
    Min,
    Sum,
)

from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.user_utils import UserUtils
from tapir.wirgarten.models import CoopShareTransaction

if TYPE_CHECKING:
    from tapir.wirgarten.models import (
        Member,
    )


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
            ExportSegmentColumn(
                id="member_full_address",
                display_name="Anschrift",
                description="",
                get_value=cls.get_value_member_full_address,
            ),
            ExportSegmentColumn(
                id="member_share_quantity",
                display_name="Anzahl Anteile",
                description="",
                get_value=cls.get_value_member_share_quantity,
            ),
            ExportSegmentColumn(
                id="member_admission_date",
                display_name="Beitrittsdatum",
                description="",
                get_value=cls.get_value_member_admission_date,
            ),
            ExportSegmentColumn(
                id="member_termination_date",
                display_name="Austrittsdatum",
                description="",
                get_value=cls.get_value_member_termination_date,
            ),
            ExportSegmentColumn(
                id="member_share_history",
                display_name="Anteilshistorie",
                description="",
                get_value=cls.get_value_member_share_history,
            ),
            ExportSegmentColumn(
                id="member_share_quantity_cancelled_in_previous_year",
                display_name="Anzahl gekündigte Anteile im Vorjahr",
                description="",
                get_value=cls.get_value_member_share_quantity_cancelled_in_previous_year,
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

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=reference_datetime.date(), cache=cache
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

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=reference_datetime.date(), cache=cache
        )
        nb_jokers = Joker.objects.filter(
            date__gte=growing_period.start_date,
            date__lte=reference_datetime,
            member=member,
        ).count()
        date_from = growing_period.start_date.strftime("%d.%m.%Y")
        date_to = reference_datetime.strftime("%d.%m.%Y")
        return f"Gutschrift {nb_jokers} genutzte Joker in Vertragsjahr {date_from}-{date_to}"

    @classmethod
    def get_value_member_full_address(cls, member: Member, _, __):
        return UserUtils.build_display_address(
            member.street, member.street_2, member.postcode, member.city
        )

    @classmethod
    def get_value_member_share_quantity(
        cls, member: Member, reference_datetime: datetime.datetime, _
    ):
        return (
            member.coopsharetransaction_set.filter(
                valid_at__lte=reference_datetime
            ).aggregate(quantity=Sum(F("quantity")))["quantity"]
            or 0
        )

    @classmethod
    def get_value_member_share_history(
        cls, member: Member, reference_datetime: datetime.datetime, _
    ):
        return "\n".join(
            f"{transaction.quantity:+} am {transaction.valid_at.strftime('%d.%m.%Y')}"
            for transaction in member.coopsharetransaction_set.filter(
                valid_at__lte=reference_datetime
            ).order_by("valid_at")
        )

    @classmethod
    def get_value_member_admission_date(cls, member: Member, _, __):
        min_valid_at = member.coopsharetransaction_set.aggregate(
            min_valid_at=Min("valid_at")
        )["min_valid_at"]
        if not min_valid_at:
            return ""
        return min_valid_at.strftime("%d.%m.%Y")

    @classmethod
    def get_value_member_termination_date(cls, member: Member, _, __):
        agg = member.coopsharetransaction_set.aggregate(
            max_valid_at=Max("valid_at"),
            quantity=Sum(F("quantity")),
        )
        if agg["quantity"] or not agg["max_valid_at"]:
            return ""
        return agg["max_valid_at"].strftime("%d.%m.%Y")

    @classmethod
    def get_value_member_share_quantity_cancelled_in_previous_year(
        cls, member: Member, reference_datetime: datetime.datetime, _
    ):
        year = reference_datetime.year
        timerange = (
            datetime.datetime(year - 1, 1, 1),
            datetime.datetime(year, 1, 1) - datetime.timedelta(milliseconds=1),
        )
        return -(
            member.coopsharetransaction_set.filter(
                transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
                valid_at__range=timerange,
            ).aggregate(quantity=Sum(F("quantity")))["quantity"]
            or 0
        )
