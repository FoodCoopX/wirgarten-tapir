from decimal import Decimal

from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape

from tapir.bidding_round.models import Bid
from tapir.wirgarten.utils import format_currency, format_date


class BiddingRoundMailTokenBuilder:
    @classmethod
    def build_bid_tokens(cls, bid: Bid, cache: dict) -> dict:
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        effective_position = BiddingRoundStatsService.get_default_position(
            bid.round, cache=cache
        )
        return {
            "round_name": escape(bid.round.name),
            "bid_items_html": cls._build_items_html(bid, effective_position, cache),
            "bid_total_per_year": format_currency(
                cls._get_bid_total_per_year(bid, effective_position, cache)
            ),
            "pickup_location": (
                escape(bid.pickup_location.name) if bid.pickup_location else ""
            ),
            "bid_link": cls._build_bid_link(),
            "bid_end_date": format_date(bid.round.end_at),
        }

    @classmethod
    def _build_bid_link(cls) -> str:
        try:
            # Absolute URL, so the link is usable in an email.
            return settings.SITE_URL + reverse("bidding_rounds:bidding_rounds")
        except NoReverseMatch:
            return ""

    @classmethod
    def _get_bid_total_per_year(cls, bid, effective_position, cache) -> Decimal:
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        return sum(
            (
                BiddingRoundStatsService.get_effective_amount(
                    item, bid.round, cache=cache, position=effective_position
                )
                * item.quantity
                * 12
                for item in bid.items.all()
            ),
            Decimal("0"),
        )

    @classmethod
    def _build_items_html(cls, bid, effective_position, cache) -> str:
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        items = []
        for item in bid.items.select_related("product", "round_product__product_type"):
            amount = BiddingRoundStatsService.get_effective_amount(
                item, bid.round, cache=cache, position=effective_position
            )
            items.append(
                f"{escape(item.round_product.product_type.name)} "
                f"({escape(item.product.name)}): "
                f"{item.quantity} x {format_currency(amount)} = "
                f"{format_currency(amount * item.quantity * 12)} pro Jahr"
            )
        return "<br />".join(items)
