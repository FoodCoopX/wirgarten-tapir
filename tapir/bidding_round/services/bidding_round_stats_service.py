from decimal import Decimal, InvalidOperation

from tapir.bidding_round.config import BIDDING_ROUND_PROCEDURE_BID_RANGE
from tapir.bidding_round.models import Bid, BiddingRound, BiddingRoundProductPrice
from tapir.bidding_round.serializers import RoundResultsResponseSerializer
from tapir.bidding_round.services.product_size_service import ProductSizeService
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Product

BID_RANGE_POSITION_MIN = Decimal("0")
BID_RANGE_POSITION_MAX = Decimal("100")
COVERAGE_STATUS_GREEN_PERCENT = 100.0
COVERAGE_STATUS_YELLOW_PERCENT = 90.0
RECOMMENDED_COVERAGE_PERCENT = 90.0
LEVEL_KEYS = {1: "green", 2: "yellow", 3: "red"}
BID_RANGE_LEVEL_KEYS = {1: "green", 2: "red"}


class BiddingRoundStatsService:
    @classmethod
    def get_target_per_year(cls, bidding_round: BiddingRound) -> Decimal:
        return bidding_round.target_amount_per_year or Decimal("0")

    @classmethod
    def get_level_position(cls, level: int, bidding_round) -> Decimal:
        """Position of a bid level on the 0/100 axis.

        The bid range has two levels (green at 0, red at 100); the simple
        procedure keeps the 0/50/100 axis for one to three levels.
        """
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            return Decimal("0") if level == 1 else Decimal("100")
        return Decimal(str((level - 1) * 50))

    @classmethod
    def clamp_position(cls, position) -> Decimal:
        try:
            value = Decimal(str(position))
        except (TypeError, ValueError, InvalidOperation):
            value = Decimal("50")
        return min(max(value, BID_RANGE_POSITION_MIN), BID_RANGE_POSITION_MAX)

    @classmethod
    def get_default_position(cls, bidding_round) -> Decimal:
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            return Decimal("50")
        return cls.get_level_position(
            cls.get_recommended_level(bidding_round), bidding_round
        )

    @staticmethod
    def _first_amount(*amounts) -> Decimal:
        for amount in amounts:
            if amount is not None:
                return amount
        return Decimal("0")

    @staticmethod
    def get_counting_amount(bid: Bid, bidding_round=None) -> Decimal:
        """The amount that counts for totals: the mid position of the range."""
        if bidding_round is None:
            bidding_round = bid.round
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            green = bid.amount_1 or bid.amount_2 or Decimal("0")
            red = bid.amount_2 or bid.amount_1 or Decimal("0")
            return (green + red) / Decimal("2")
        return bid.amount_2 or bid.amount_1 or bid.amount_3 or Decimal("0")

    @classmethod
    def get_amount_for_position(cls, bid: Bid, position, bidding_round=None) -> Decimal:
        """Amount per share at a position on the 0/100 axis.

        The bid range interpolates linearly between green (0) and red (100).
        Simple rounds keep the 0/50/100 interpolation; missing levels fall back
        to the middle amount, so a one-amount round yields a constant value.
        """
        position = cls.clamp_position(position)
        if bidding_round is None:
            bidding_round = bid.round
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            green = cls._first_amount(bid.amount_1, bid.amount_2)
            red = cls._first_amount(bid.amount_2, bid.amount_1)
            return green + (red - green) * position / Decimal("100")
        base = cls._first_amount(bid.amount_2, bid.amount_1, bid.amount_3)
        green = bid.amount_1 if bid.amount_1 is not None else base
        yellow = bid.amount_2 if bid.amount_2 is not None else base
        red = bid.amount_3 if bid.amount_3 is not None else base
        if position <= 50:
            return green + (yellow - green) * (position / Decimal("50"))
        return yellow + (red - yellow) * ((position - Decimal("50")) / Decimal("50"))

    @classmethod
    def get_effective_amount(cls, bid: Bid, position, bidding_round=None) -> Decimal:
        return cls.get_amount_for_position(bid, position, bidding_round)

    @classmethod
    def get_reached_per_year(cls, bidding_round, position=None) -> Decimal:
        if position is None:
            position = cls.get_default_position(bidding_round)
        return sum(
            (
                cls.get_bid_monthly_amount(bid, position, bidding_round) * 12
                for bid in cls._bids(bidding_round)
            ),
            Decimal("0"),
        )

    @classmethod
    def get_coverage_percent(cls, bidding_round, position=None) -> float:
        target = cls.get_target_per_year(bidding_round)
        if target == 0:
            return 0.0
        return float(cls.get_reached_per_year(bidding_round, position) / target * 100)

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
        cls, bidding_round, position=None, *, cache: dict
    ) -> Decimal:
        if position is None:
            position = cls.get_default_position(bidding_round)
        total_amount = Decimal("0")
        total_shares = Decimal("0")
        for bid in cls._bids(bidding_round):
            total_amount += cls.get_bid_monthly_amount(bid, position, bidding_round)
            total_shares += (
                cls.get_product_size(bid.product, bidding_round, cache) * bid.quantity
            )
        if total_shares == 0:
            return Decimal("0")
        return total_amount / total_shares

    @classmethod
    def get_bidder_average_per_month(cls, bidding_round, position=None) -> Decimal:
        if position is None:
            position = cls.get_default_position(bidding_round)
        amounts = [
            cls.get_bid_monthly_amount(bid, position, bidding_round)
            for bid in cls._bids(bidding_round)
        ]
        if not amounts:
            return Decimal("0")
        return sum(amounts, Decimal("0")) / len(amounts)

    @classmethod
    def get_bid_monthly_amount(
        cls, bid: Bid, position=None, bidding_round=None
    ) -> Decimal:
        return cls.get_effective_amount(bid, position, bidding_round) * bid.quantity

    @classmethod
    def get_recommended_level(cls, bidding_round) -> int:
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            return 2
        levels = max(1, min(3, bidding_round.bid_levels))
        for level in range(1, levels + 1):
            if (
                cls.get_coverage_percent(
                    bidding_round,
                    cls.get_level_position(level, bidding_round),
                )
                >= RECOMMENDED_COVERAGE_PERCENT
            ):
                return level
        return levels

    @classmethod
    def get_coverage_status(cls, bidding_round, position=None) -> str:
        coverage = cls.get_coverage_percent(bidding_round, position)
        if coverage >= COVERAGE_STATUS_GREEN_PERCENT:
            return "green"
        if coverage >= COVERAGE_STATUS_YELLOW_PERCENT:
            return "yellow"
        return "red"

    @classmethod
    def build_levels_evaluation(cls, bidding_round) -> dict:
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            level_keys = BID_RANGE_LEVEL_KEYS
        else:
            level_keys = LEVEL_KEYS
        return {
            level_key: {
                "reached_per_year": str(
                    cls.get_reached_per_year(
                        bidding_round,
                        cls.get_level_position(level, bidding_round),
                    )
                ),
                "coverage_percent": cls.get_coverage_percent(
                    bidding_round,
                    cls.get_level_position(level, bidding_round),
                ),
                "coverage_status": cls.get_coverage_status(
                    bidding_round,
                    cls.get_level_position(level, bidding_round),
                ),
                "bidder_average_per_month": str(
                    cls.get_bidder_average_per_month(
                        bidding_round,
                        cls.get_level_position(level, bidding_round),
                    )
                ),
            }
            for level, level_key in level_keys.items()
        }

    @classmethod
    def get_capacity_shares(cls, bidding_round, cache) -> Decimal:
        capacity = TapirCache.get_product_type_capacity_at_date(
            cache=cache,
            product_type=bidding_round.product_type,
            reference_date=bidding_round.growing_period.start_date,
        )
        if capacity is None or capacity.capacity is None:
            return Decimal("0")
        return Decimal(capacity.capacity).quantize(Decimal("0.01"))

    @classmethod
    def get_current_shares(cls, bidding_round, cache) -> Decimal:
        total = Decimal("0")
        for bid in cls._bids(bidding_round):
            total += (
                cls.get_product_size(bid.product, bidding_round, cache) * bid.quantity
            )
        return total

    @classmethod
    def get_utilization_percent(cls, capacity, current) -> float:
        if capacity == 0:
            return 0.0
        return float(current / capacity * 100)

    @classmethod
    def build_public_evaluation(cls, bidding_round, cache) -> dict:
        position = cls.get_default_position(bidding_round)
        capacity_shares = cls.get_capacity_shares(bidding_round, cache)
        current_shares = cls.get_current_shares(bidding_round, cache)
        return {
            "bidding_procedure": bidding_round.bidding_procedure,
            "bid_levels": bidding_round.bid_levels,
            "recommended_level": cls.get_recommended_level(bidding_round),
            "bid_range_position": float(position),
            "coverage_status": cls.get_coverage_status(bidding_round, position),
            "target_per_year": str(cls.get_target_per_year(bidding_round)),
            "capacity_shares": str(capacity_shares),
            "current_shares": str(current_shares),
            "utilization_percent": cls.get_utilization_percent(
                capacity_shares, current_shares
            ),
            "coverage_percent": cls.get_coverage_percent(bidding_round, position),
            "bidder_average_per_month": str(
                cls.get_bidder_average_per_month(bidding_round, position)
            ),
            "levels": cls.build_levels_evaluation(bidding_round),
        }

    @classmethod
    def build_admin_evaluation(cls, bidding_round, cache, position=None) -> dict:
        if position is None:
            position = cls.get_default_position(bidding_round)
        position = cls.clamp_position(position)
        bids = bidding_round.bids.select_related("member", "product")
        data = {
            "bidding_procedure": bidding_round.bidding_procedure,
            "bid_levels": bidding_round.bid_levels,
            "bid_range_position": float(position),
            "recommended_level": cls.get_recommended_level(bidding_round),
            "coverage_status": cls.get_coverage_status(bidding_round, position),
            "levels": cls.build_levels_evaluation(bidding_round),
            "target_per_year": str(cls.get_target_per_year(bidding_round)),
            "reached_per_year": str(cls.get_reached_per_year(bidding_round, position)),
            "coverage_percent": cls.get_coverage_percent(bidding_round, position),
            "bidder_count": bids.count(),
            "bidder_average_per_month": str(
                cls.get_bidder_average_per_month(bidding_round, position)
            ),
            "bids": bids,
        }
        return RoundResultsResponseSerializer(data, context={"position": position}).data

    @classmethod
    def _bids(cls, bidding_round):
        return bidding_round.bids.select_related("product")
