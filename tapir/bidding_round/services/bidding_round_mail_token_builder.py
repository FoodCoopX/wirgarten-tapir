from decimal import Decimal

from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape

from tapir.bidding_round.models import Bid
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.utils import format_currency, format_date


class BiddingRoundMailTokenBuilder:
    @classmethod
    def build_bid_tokens(cls, bid: Bid, cache: dict) -> dict:
        position = BiddingRoundStatsService.get_default_position(bid.round, cache=cache)
        items = list(
            bid.items.select_related("product", "round_product_type__product_type")
        )
        pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
            member=bid.member,
            reference_date=bid.round.growing_period.start_date,
            cache=cache,
        )
        return {
            "round_name": escape(bid.round.name),
            "bid_items_html": cls._build_items_html(items, bid, position),
            "bid_total_per_year": format_currency(
                cls._get_bid_total_per_year(items, bid, position)
            ),
            "pickup_location": (
                escape(pickup_location.name) if pickup_location is not None else ""
            ),
            "bid_link": cls._build_bid_link(),
            "bid_end_date": format_date(bid.round.end_at),
        }

    @classmethod
    def _build_bid_link(cls) -> str:
        try:
            return settings.SITE_URL + reverse("bidding_rounds:bidding_rounds")
        except NoReverseMatch:
            return ""

    @classmethod
    def _get_bid_total_per_year(cls, items, bid, position) -> Decimal:
        return sum(
            (
                BiddingRoundStatsService.get_item_monthly_amount(
                    item, position, bid.round
                )
                * 12
                for item in items
            ),
            Decimal("0"),
        )

    @classmethod
    def _build_items_html(cls, items, bid, position) -> str:
        lines = []
        for item in items:
            monthly = BiddingRoundStatsService.get_item_monthly_amount(
                item, position, bid.round
            )
            quantity_label = (
                "1 Anteil" if item.quantity == 1 else f"{item.quantity} Anteile"
            )
            lines.append(
                f"{escape(item.round_product_type.product_type.name)} "
                f"({escape(item.product.name)}, {quantity_label}): "
                f"{format_currency(monthly)} = "
                f"{format_currency(monthly * 12)}"
                " pro Jahr"
            )
        return "<br />".join(lines)
