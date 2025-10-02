from __future__ import annotations

import datetime
import locale
from functools import partial
from typing import TYPE_CHECKING, Dict

from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.user_utils import UserUtils
from tapir.wirgarten.service.products import get_current_growing_period
from tapir.wirgarten.utils import format_date

if TYPE_CHECKING:
    from tapir.wirgarten.models import Member, Product


class MemberColumnProvider:
    @classmethod
    def get_member_columns(cls):
        base_columns = [
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
                id="member_pickup_location",
                display_name="Abholort",
                description="",
                get_value=cls.get_value_member_pickup_location,
            ),
            ExportSegmentColumn(
                id="member_post_address",
                display_name="Post Adresse",
                description="",
                get_value=cls.get_value_member_post_address,
            ),
            ExportSegmentColumn(
                id="member_entry_date",
                display_name="Eintrittsdatum",
                description="Eintrittsdatum in der Genossenschaft",
                get_value=cls.get_value_member_entry_date,
            ),
            ExportSegmentColumn(
                id="member_membership_status",
                display_name="Mitgliedschaftsstatus",
                description="Status der Mitgliedschaft in der Genossenschaft",
                get_value=cls.get_value_member_membership_status,
            ),
            ExportSegmentColumn(
                id="member_subscription_summary",
                display_name="Produktanteile",
                description="Zusammenfassung der aktueller Verträge",
                get_value=cls.get_value_member_subscription_summary,
            ),
            ExportSegmentColumn(
                id="member_payment_rhythm",
                display_name="Zahlungsintervall",
                description="",
                get_value=cls.get_value_member_payment_rhythm,
            ),
            ExportSegmentColumn(
                id="member_amount_to_pay",
                display_name="Beitragshöhe",
                description="",
                get_value=cls.get_value_member_amount_to_pay,
            ),
            ExportSegmentColumn(
                id="member_solidarity_contribution",
                display_name="Solidarbeitrag",
                description="",
                get_value=cls.get_value_member_solidarity_contribution,
            ),
            ExportSegmentColumn(
                id="member_membership_end_date",
                display_name="Kündigungsdatum (Genossenschaft)",
                description="",
                get_value=cls.get_value_member_membership_end_date,
            ),
            ExportSegmentColumn(
                id="member_subscription_end_dates",
                display_name="Kündigungsdaten (Produkte)",
                description="",
                get_value=cls.get_value_member_subscription_end_dates,
            ),
        ]
        return base_columns + cls.build_product_columns()

    @classmethod
    def build_product_columns(cls):
        from tapir.wirgarten.models import Product

        columns = []
        for product in Product.objects.all():
            columns.append(
                ExportSegmentColumn(
                    id=f"member_product_type_{product.name}_{product.id}",
                    display_name=f"Anzahl an {product.name}",
                    description=f"Anzahl an Produktanteil für {product.name}, nur aktive Verträge",
                    get_value=partial(
                        cls.get_value_amount_active_subscriptions,
                        product=product,
                    ),
                )
            )
        return columns

    @classmethod
    def get_value_amount_active_subscriptions(
        cls,
        member: Member,
        reference_datetime: datetime.datetime,
        cache: dict,
        product: Product,
    ):
        subscriptions = [
            subscription
            for subscription in TapirCache.get_subscriptions_active_at_date(
                reference_date=reference_datetime.date(), cache=cache
            )
            if subscription.member_id == member.id
            and subscription.product_id == product.id
        ]

        return str(sum([subscription.quantity for subscription in subscriptions]))

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

    @classmethod
    def get_value_member_pickup_location(
        cls, member: Member, reference_datetime: datetime.datetime, cache: Dict
    ):
        pickup_location_id = (
            MemberPickupLocationService.get_member_pickup_location_id_from_cache(
                member_id=member.id,
                reference_date=reference_datetime.date(),
                cache=cache,
            )
        )
        if pickup_location_id is None:
            return "Keine"

        return TapirCache.get_pickup_location_by_id(
            cache=cache, pickup_location_id=pickup_location_id
        ).name

    @classmethod
    def get_value_member_post_address(cls, member: Member, _, __):
        return UserUtils.build_display_address(
            street=member.street,
            street_2=member.street_2,
            postcode=member.postcode,
            city=member.city,
        )

    @classmethod
    def get_value_member_entry_date(cls, member: Member, _, __):
        return MembershipCancellationManager.get_coop_entry_date(member)

    @classmethod
    def get_value_member_membership_status(
        cls, member: Member, reference_datetime: datetime.datetime, cache: dict
    ):
        nb_shares = TapirCache.get_number_of_shares_for_member_id_at_date(
            member_id=member.id, reference_date=reference_datetime.date(), cache=cache
        )
        if nb_shares == 0:
            return "Inaktiv"
        return "Aktiv"

    @classmethod
    def get_value_member_subscription_summary(
        cls, member: Member, reference_datetime: datetime.datetime, cache: dict
    ):
        product_to_quantity_map = {
            product.name: cls.get_value_amount_active_subscriptions(
                member=member,
                reference_datetime=reference_datetime,
                cache=cache,
                product=product,
            )
            for product in TapirCache.get_all_products(cache=cache)
        }
        return ", ".join(
            [
                f"{product_name}:{quantity}"
                for product_name, quantity in product_to_quantity_map.items()
                if quantity != "0"
            ]
        )

    @classmethod
    def get_value_member_payment_rhythm(cls, _, __, ___):
        # Temporary column before we merge the payment rhythm logic from the biotop-dev branch to this prod branch
        return "Monatlich"

    @classmethod
    def get_value_member_amount_to_pay(
        cls, member: Member, reference_datetime: datetime.datetime, cache: dict
    ):
        subscriptions = [
            subscription
            for subscription in TapirCache.get_subscriptions_active_at_date(
                reference_date=reference_datetime.date(), cache=cache
            )
            if subscription.member_id == member.id
        ]

        amount_to_pay = sum(
            [
                subscription.total_price(
                    reference_date=reference_datetime.date(), cache=cache
                )
                for subscription in subscriptions
            ]
        )

        return locale.format_string("%.2f", amount_to_pay)

    @classmethod
    def get_value_member_solidarity_contribution(
        cls, member: Member, reference_datetime: datetime.datetime, cache: dict
    ):
        # Temporary column, needs to be updated when we merge the solibeitrag story US 5.2.4 #618
        return "0"

    @classmethod
    def get_value_member_membership_end_date(cls, member: Member, _, cache: dict):
        transactions = TapirCache.get_all_coop_share_transactions_by_member_id(
            cache=cache
        ).get(member.id, None)
        if transactions is None or len(transactions) == 0:
            return ""

        nb_shares_after_last_transaction = (
            TapirCache.get_number_of_shares_for_member_id_at_date(
                cache=cache,
                member_id=member.id,
                reference_date=transactions[-1].valid_at,
            )
        )
        if nb_shares_after_last_transaction > 0:
            return ""

        return f"{format_date(transactions[-1].valid_at)}: {transactions[-1].quantity} Anteile"

    @classmethod
    def get_value_member_subscription_end_dates(cls, member: Member, _, cache: dict):
        member_subscriptions = [
            subscription
            for subscription in TapirCache.get_all_subscriptions(cache=cache)
            if subscription.member_id == member.id
        ]

        end_dates = []
        for product in TapirCache.get_all_products(cache=cache):
            product_subscriptions = [
                subscription
                for subscription in member_subscriptions
                if subscription.product_id == product.id
            ]
            if len(product_subscriptions) == 0:
                continue

            all_subscriptions_cancelled = all(
                [
                    subscription.cancellation_ts is not None
                    for subscription in product_subscriptions
                ]
            )
            if not all_subscriptions_cancelled:
                continue

            max_end_date = max(
                [subscription.end_date for subscription in product_subscriptions]
            )
            end_dates.append(f"{product.name}:{format_date(max_end_date)}")

        return ", ".join(end_dates)
