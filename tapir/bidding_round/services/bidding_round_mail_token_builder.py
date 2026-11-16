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
        pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
            member=bid.member,
            reference_date=bid.round.growing_period.start_date,
            cache=cache,
        )
        return {
            "round_name": escape(bid.round.name),
            "bid_items_html": cls._build_bid_html(bid, position),
            "bid_total_per_year": format_currency(
                cls._get_bid_total_per_year(bid, position)
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
    def _get_bid_total_per_year(cls, bid: Bid, position) -> Decimal:
        return (
            BiddingRoundStatsService.get_bid_monthly_amount(bid, position, bid.round)
            * 12
        )

    @classmethod
    def _build_bid_html(cls, bid: Bid, position) -> str:
        monthly = BiddingRoundStatsService.get_bid_monthly_amount(
            bid, position, bid.round
        )
        quantity_label = "1 Anteil" if bid.quantity == 1 else f"{bid.quantity} Anteile"
        return (
            f"{escape(bid.round.product_type.name)} "
            f"({escape(bid.product.name)}, {quantity_label}): "
            f"{format_currency(monthly)} = "
            f"{format_currency(monthly * 12)}"
            " pro Jahr"
        )
