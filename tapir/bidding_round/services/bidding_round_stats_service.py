from decimal import Decimal

from tapir.bidding_round.models import BidItem, BiddingRoundProductPrice
from tapir.bidding_round.services.bidding_round_view_service import (
    BiddingRoundViewService,
)


class BiddingRoundStatsService:
    @classmethod
    def get_target_per_year(cls, bidding_round) -> Decimal:
        round_product_type = bidding_round.product_types.first()
        if round_product_type is None:
            return Decimal("0")
        return round_product_type.target_amount_per_year or Decimal("0")

    @classmethod
    def get_reached_per_year(cls, bidding_round) -> Decimal:
        return sum(
            (
                cls.get_item_monthly_amount(item) * 12
                for item in cls._items(bidding_round)
            ),
            Decimal("0"),
        )

    @classmethod
    def get_coverage_percent(cls, bidding_round) -> float:
        target = cls.get_target_per_year(bidding_round)
        if target == 0:
            return 0.0
        return float(cls.get_reached_per_year(bidding_round) / target * 100)

    @classmethod
    def get_bidder_count(cls, bidding_round) -> int:
        return bidding_round.bids.count()

    @classmethod
    def get_product_size(cls, product, bidding_round, cache: dict) -> Decimal:
        price = BiddingRoundProductPrice.objects.filter(
            round_product_type__round=bidding_round,
            product=product,
        ).first()
        if price is None or price.size is None:
            return Decimal("0")
        return Decimal(price.size)

    @classmethod
    def get_bidder_average_per_share_per_month(
        cls, bidding_round, cache: dict
    ) -> Decimal:
        total_amount = Decimal("0")
        total_shares = Decimal("0")
        for item in cls._items(bidding_round):
            total_amount += (item.amount_1 or Decimal("0")) * item.quantity
            total_shares += (
                cls.get_product_size(item.product, bidding_round, cache) * item.quantity
            )
        if total_shares == 0:
            return Decimal("0")
        return total_amount / total_shares

    @classmethod
    def get_bidder_average_per_month(cls, bidding_round) -> Decimal:
        amounts = [
            cls.get_item_monthly_amount(item)
            for item in cls._items(bidding_round)
            if item.amount_1 is not None
        ]
        if not amounts:
            return Decimal("0")
        return sum(amounts, Decimal("0")) / len(amounts)

    @classmethod
    def get_item_monthly_amount(cls, item) -> Decimal:
        return (item.amount_1 or Decimal("0")) * item.quantity

    @classmethod
    def build_admin_evaluation(cls, bidding_round, cache) -> dict:
        rows = []
        for bid in bidding_round.bids.select_related("member").prefetch_related(
            "items__product"
        ):
            items = list(bid.items.select_related("product").all())
            amount_per_month = sum(
                (cls.get_item_monthly_amount(item) for item in items), Decimal("0")
            )
            rows.append(
                {
                    "bid_id": bid.id,
                    "member_id": bid.member_id,
                    "member_name": str(bid.member),
                    "email": bid.member.email,
                    "amount_per_month": str(amount_per_month),
                    "amount_per_year": str(amount_per_month * 12),
                    "items": [
                        BiddingRoundViewService.serialize_bid_item(item)
                        for item in items
                    ],
                }
            )

        return {
            "target_per_year": str(cls.get_target_per_year(bidding_round)),
            "reached_per_year": str(cls.get_reached_per_year(bidding_round)),
            "coverage_percent": cls.get_coverage_percent(bidding_round),
            "bidder_count": cls.get_bidder_count(bidding_round),
            "bidder_average_per_month": str(
                cls.get_bidder_average_per_month(bidding_round)
            ),
            "bids": rows,
        }

    @classmethod
    def _items(cls, bidding_round):
        return BidItem.objects.filter(bid__round=bidding_round).select_related(
            "product"
        )
