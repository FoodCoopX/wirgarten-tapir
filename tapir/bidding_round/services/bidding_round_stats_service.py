from decimal import Decimal

from tapir.bidding_round.models import (
    Bid,
    BiddingRound,
    BiddingRoundProductPrice,
)
from tapir.bidding_round.services.product_size_service import ProductSizeService
from tapir.wirgarten.models import Product


class BiddingRoundStatsService:
    @classmethod
    def get_target_per_year(cls, bidding_round: BiddingRound) -> Decimal:
        return bidding_round.target_amount_per_year or Decimal("0")

    @classmethod
    def get_reached_per_year(cls, bidding_round: BiddingRound) -> Decimal:
        return sum(
            (cls.get_bid_monthly_amount(bid) * 12 for bid in bidding_round.bids.all()),
            Decimal("0"),
        )

    @classmethod
    def get_coverage_percent(cls, bidding_round: BiddingRound) -> float:
        target = cls.get_target_per_year(bidding_round)
        if target == 0:
            return 0.0
        return float(cls.get_reached_per_year(bidding_round) / target * 100)

    @classmethod
    def get_product_size(
        cls, product: Product, bidding_round: BiddingRound, cache: dict
    ) -> Decimal:
        price = BiddingRoundProductPrice.objects.filter(
            round=bidding_round,
            product=product,
        ).first()
        if price is not None and price.size is not None:
            return Decimal(price.size)
        size = ProductSizeService.get_size(
            product, bidding_round.growing_period, cache=cache
        )
        return size if size is not None else Decimal("0")

    @classmethod
    def get_bidder_average_per_share_per_month(
        cls, bidding_round: BiddingRound, cache: dict
    ) -> Decimal:
        total_amount = Decimal("0")
        total_shares = Decimal("0")
        for bid in bidding_round.bids.all():
            total_amount += cls.get_bid_monthly_amount(bid)
            total_shares += (
                cls.get_product_size(bid.product, bidding_round, cache) * bid.quantity
            )
        if total_shares == 0:
            return Decimal("0")
        return total_amount / total_shares

    @classmethod
    def get_bidder_average_per_month(cls, bidding_round: BiddingRound) -> Decimal:
        amounts = [cls.get_bid_monthly_amount(bid) for bid in bidding_round.bids.all()]
        if not amounts:
            return Decimal("0")
        return sum(amounts, Decimal("0")) / len(amounts)

    @classmethod
    def get_bid_monthly_amount(cls, bid: Bid) -> Decimal:
        return (bid.amount_1 or Decimal("0")) * bid.quantity

    @classmethod
    def build_admin_evaluation(cls, bidding_round: BiddingRound, cache: dict) -> dict:
        rows = []
        for bid in bidding_round.bids.select_related("member", "product"):
            amount_per_month = cls.get_bid_monthly_amount(bid)
            rows.append(
                {
                    "bid_id": bid.id,
                    "member_id": bid.member_id,
                    "member_name": str(bid.member),
                    "email": bid.member.email,
                    "product_id": bid.product_id,
                    "product_name": bid.product.name,
                    "quantity": bid.quantity,
                    "amount_1": (
                        str(bid.amount_1) if bid.amount_1 is not None else None
                    ),
                    "amount_per_month": str(amount_per_month),
                    "amount_per_year": str(amount_per_month * 12),
                }
            )

        return {
            "target_per_year": str(cls.get_target_per_year(bidding_round)),
            "reached_per_year": str(cls.get_reached_per_year(bidding_round)),
            "coverage_percent": cls.get_coverage_percent(bidding_round),
            "bidder_count": bidding_round.bids.count(),
            "bidder_average_per_month": str(
                cls.get_bidder_average_per_month(bidding_round)
            ),
            "bids": rows,
        }
