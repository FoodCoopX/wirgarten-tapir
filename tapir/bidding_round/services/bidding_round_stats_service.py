from decimal import Decimal, InvalidOperation

from tapir.associations.models import AssociationMembershipType
from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.bidding_round.config import BIDDING_ROUND_PROCEDURE_BID_RANGE
from tapir.bidding_round.models import Bid, BiddingRound, BiddingRoundProductPrice
from tapir.bidding_round.serializers import RoundResultsResponseSerializer
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.bidding_round.services.product_size_service import ProductSizeService
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Product
from tapir.wirgarten.utils import legal_status_is_association

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
    def get_default_position(cls, bidding_round, cache: dict) -> Decimal:
        if bidding_round.average_bid_locked_at is not None:
            return cls.clamp_position(bidding_round.locked_bid_range_position)
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            return Decimal("50")
        return cls.get_level_position(
            cls.get_recommended_level(bidding_round, cache), bidding_round
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
    def get_surcharge_factor(cls, bidding_round) -> Decimal:
        if bidding_round.average_bid_locked_at is None:
            return Decimal("1")
        return Decimal("1") + Decimal(bidding_round.locked_surcharge_percent) / 100

    @classmethod
    def _apply_surcharge_and_cap(
        cls, amount, bid: Bid, bidding_round, factor, surcharge_on_bids
    ) -> Decimal:
        if not surcharge_on_bids:
            return amount
        amount = amount * factor
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            red = bid.amount_2 or bid.amount_1 or Decimal("0")
            amount = min(amount, red)
        return amount

    @classmethod
    def get_effective_amount(cls, bid: Bid, position, bidding_round=None) -> Decimal:
        amount = cls.get_amount_for_position(bid, position, bidding_round)
        if bidding_round is None:
            return amount
        return cls._apply_surcharge_and_cap(
            amount,
            bid,
            bidding_round,
            cls.get_surcharge_factor(bidding_round),
            bool(
                bidding_round.average_bid_locked_at is not None
                and bidding_round.locked_surcharge_on_bids
            ),
        )

    @classmethod
    def build_locked_average_bid(
        cls,
        bidding_round,
        position,
        surcharge_percent,
        surcharge_on_bids,
        surcharge_on_average,
        cache,
    ) -> dict:
        factor = (
            Decimal("1") + Decimal(str(surcharge_percent or 0)) / 100
            if surcharge_on_bids
            else Decimal("1")
        )
        total_amount = Decimal("0")
        total_shares = Decimal("0")
        for bid in cls._bids(bidding_round, cache):
            amount = cls.get_amount_for_position(bid, position, bidding_round)
            total_amount += (
                cls._apply_surcharge_and_cap(
                    amount,
                    bid,
                    bidding_round,
                    factor,
                    bool(surcharge_on_bids),
                )
                * bid.quantity
            )
            total_shares += (
                cls._get_size(bid.product, bidding_round, cache) * bid.quantity
            )
        if total_shares == 0:
            per_share_month = Decimal("0")
        else:
            per_share_month = total_amount / total_shares
        if surcharge_on_average:
            per_share_month = per_share_month * (
                Decimal("1") + Decimal(str(surcharge_percent or 0)) / 100
            )
        return {
            "bidder_amount_per_share_per_month": per_share_month.quantize(
                Decimal("0.01")
            ),
            "bidder_amount_per_share_per_year": (per_share_month * 12).quantize(
                Decimal("0.01")
            ),
        }

    @classmethod
    def get_reached_per_year(
        cls, bidding_round, position=None, *, cache: dict
    ) -> Decimal:
        if position is None:
            position = cls.get_default_position(bidding_round, cache)
        total = sum(
            (
                cls.get_bid_monthly_amount(bid, position, bidding_round) * 12
                for bid in cls._bids(bidding_round, cache)
            ),
            Decimal("0"),
        )
        if cls.are_auto_renewed_included(bidding_round, cache):
            total += cls.get_auto_renewed_per_year(bidding_round, cache)
        return total

    @classmethod
    def are_auto_renewed_included(cls, bidding_round, cache: dict) -> bool:
        return bidding_round.include_auto_renewed

    @classmethod
    def _get_size(
        cls, product: Product, bidding_round: BiddingRound, cache: dict
    ) -> Decimal:
        return cls.get_product_size(product, bidding_round, cache)

    @classmethod
    def get_auto_renewed_by_member(cls, bidding_round, cache: dict) -> dict:
        cache_key = ("bidding_round_auto_renewed", bidding_round.id)
        if cache_key in cache:
            return cache[cache_key]

        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        product_type_id = bidding_round.product_type_id
        prices_by_product_id = {
            price.product_id: price
            for price in BiddingRoundProductPrice.objects.filter(round=bidding_round)
        }
        try:
            renewing_subscriptions = AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=bidding_round.growing_period.start_date,
                cache=cache,
            )
        except KeyError:
            renewing_subscriptions = []

        result = {}
        for subscription in renewing_subscriptions:
            if subscription.member_id in bid_member_ids:
                continue
            if subscription.product.type_id != product_type_id:
                continue
            price = prices_by_product_id.get(subscription.product_id)
            reference_value = (
                price.reference_value if price is not None else Decimal("0")
            )
            monthly = (reference_value or Decimal("0")) * subscription.quantity
            entry = result.setdefault(
                subscription.member_id,
                {
                    "member_id": subscription.member_id,
                    "member_name": str(subscription.member),
                    "monthly_reference": Decimal("0"),
                    "yearly_reference": Decimal("0"),
                },
            )
            entry["monthly_reference"] += monthly
            entry["yearly_reference"] += monthly * 12

        cache[cache_key] = result
        return result

    @classmethod
    def get_auto_renewed_per_year(cls, bidding_round, cache: dict) -> Decimal:
        return sum(
            (
                entry["yearly_reference"]
                for entry in cls.get_auto_renewed_by_member(
                    bidding_round, cache
                ).values()
            ),
            Decimal("0"),
        )

    @classmethod
    def _get_auto_renewed_shares(cls, bidding_round, cache) -> Decimal:
        product_type_id = bidding_round.product_type_id
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        try:
            subscriptions = AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=bidding_round.growing_period.start_date,
                cache=cache,
            )
        except KeyError:
            subscriptions = []

        total = Decimal("0")
        for subscription in subscriptions:
            if subscription.member_id in bid_member_ids:
                continue
            if subscription.product.type_id != product_type_id:
                continue
            total += (
                cls._get_size(subscription.product, bidding_round, cache)
                * subscription.quantity
            )
        return total

    @classmethod
    def build_financing_projection(
        cls, bidding_round, cache, include_auto_renewed=True
    ) -> dict:
        target_per_year = cls.get_target_per_year(bidding_round)
        capacity_shares = cls.get_capacity_shares(bidding_round, cache)
        bid_shares = cls.get_current_shares(bidding_round, cache)

        auto_renewed = (
            cls.get_auto_renewed_by_member(bidding_round, cache)
            if include_auto_renewed
            else {}
        )
        auto_euro = sum(
            (entry["yearly_reference"] for entry in auto_renewed.values()),
            Decimal("0"),
        )
        auto_shares = (
            cls._get_auto_renewed_shares(bidding_round, cache)
            if include_auto_renewed
            else Decimal("0")
        )

        extra_positions = cls.build_extra_positions(bidding_round, cache=cache)
        membership_per_year = (
            extra_positions["membership"]["reached_per_year"]
            if extra_positions["membership"]["applicable"]
            else Decimal("0")
        )
        delivery_charge_per_year = (
            extra_positions["delivery_charge"]["reached_per_year"]
            if extra_positions["delivery_charge"]["applicable"]
            else Decimal("0")
        )
        fixed_per_year = auto_euro + membership_per_year + delivery_charge_per_year

        def build_level(position):
            reached_per_year = cls.get_reached_per_year(
                bidding_round, position, cache=cache
            )
            average_per_share_per_month = (
                reached_per_year / (bid_shares * 12) if bid_shares else Decimal("0")
            )
            return {
                "reached_per_year": reached_per_year,
                "average_per_share_per_month": average_per_share_per_month.quantize(
                    Decimal("0.01")
                ),
            }

        return {
            "target_per_year": target_per_year,
            "capacity_shares": capacity_shares,
            "bid_shares": bid_shares,
            "auto_shares": auto_shares,
            "remaining_shares": max(
                capacity_shares - bid_shares - auto_shares, Decimal("0")
            ),
            "fixed_per_year": fixed_per_year,
            "auto_renew_per_year": auto_euro,
            "membership_per_year": membership_per_year,
            "delivery_charge_per_year": delivery_charge_per_year,
            "membership_included_in_product_type": False,
            "levels": {
                "green": build_level(Decimal("0")),
                "yellow": build_level(Decimal("50")),
                "red": build_level(Decimal("100")),
            },
        }

    @classmethod
    def build_non_bidder_rate_per_share(cls, bidding_round, cache) -> Decimal:
        if (
            bidding_round.average_bid_locked_at is not None
            and bidding_round.locked_bidder_average_per_share_per_month is not None
        ):
            return bidding_round.locked_bidder_average_per_share_per_month
        position = cls.get_default_position(bidding_round, cache)
        total_amount = Decimal("0")
        total_shares = Decimal("0")
        for bid in cls._bids(bidding_round, cache):
            total_amount += cls.get_effective_amount(bid, position, bidding_round)
            total_shares += cls._get_size(bid.product, bidding_round, cache)
        if total_shares == 0:
            return Decimal("0")
        rate = total_amount / total_shares
        if (
            bidding_round.average_bid_locked_at is not None
            and bidding_round.locked_surcharge_on_average
        ):
            rate = rate * (
                Decimal("1") + Decimal(bidding_round.locked_surcharge_percent) / 100
            )
        return rate.quantize(Decimal("0.01"))

    @classmethod
    def build_extra_positions(cls, bidding_round, cache) -> dict:
        product_type = bidding_round.product_type
        return {
            "membership": cls._get_membership_position(bidding_round, cache),
            "delivery_charge": cls._get_delivery_charge_position(
                bidding_round, product_type, cache
            ),
        }

    @classmethod
    def _get_membership_position(cls, bidding_round, cache) -> dict:
        position = {
            "label": "Mitgliedschaft",
            "reached_per_year": Decimal("0"),
            "applicable": False,
        }
        try:
            is_association = legal_status_is_association(cache)
        except KeyError:
            is_association = False
        if not is_association:
            return position

        membership_type = (
            AssociationMembershipType.objects.filter(
                deleted=False, hidden_in_bestell_wizard=False
            )
            .order_by("order_in_bestell_wizard")
            .first()
        )
        if membership_type is None:
            return position
        price = AssociationMembershipTypePriceGetter.get_price(
            membership_type=membership_type,
            reference_date=bidding_round.growing_period.start_date,
            cache=cache,
        )
        if not price:
            return position
        position["reached_per_year"] = price * 12 * bidding_round.bids.count()
        position["applicable"] = True
        return position

    @classmethod
    def _get_delivery_charge_position(cls, bidding_round, product_type, cache) -> dict:
        position = {
            "label": "Lieferzuschlag",
            "reached_per_year": Decimal("0"),
            "applicable": False,
        }
        if product_type is None:
            return position

        reference_date = bidding_round.growing_period.start_date
        bids_per_pickup_location = {}
        for bid in bidding_round.bids.all():
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=bid.member_id,
                    reference_date=reference_date,
                    cache=cache,
                )
            )
            if pickup_location_id is None:
                continue
            bids_per_pickup_location[pickup_location_id] = (
                bids_per_pickup_location.get(pickup_location_id, 0) + 1
            )

        charge_by_location = {
            pickup_location_id: BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
                pickup_location_id=pickup_location_id,
                product_type=product_type,
                growing_period=bidding_round.growing_period,
                cache=cache,
            )
            for pickup_location_id in bids_per_pickup_location
        }
        position["reached_per_year"] = sum(
            (
                charge_by_location.get(pickup_location_id, Decimal("0")) * count
                for pickup_location_id, count in bids_per_pickup_location.items()
            ),
            Decimal("0"),
        )
        position["applicable"] = position["reached_per_year"] > 0
        return position

    @classmethod
    def get_coverage_percent(
        cls, bidding_round, position=None, *, cache: dict
    ) -> float:
        target = cls.get_target_per_year(bidding_round)
        if target == 0:
            return 0.0
        return float(
            cls.get_reached_per_year(bidding_round, position, cache=cache)
            / target
            * 100
        )

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
        if (
            bidding_round.average_bid_locked_at is not None
            and bidding_round.locked_bidder_average_per_share_per_month is not None
        ):
            return bidding_round.locked_bidder_average_per_share_per_month
        if position is None:
            position = cls.get_default_position(bidding_round, cache)
        total_amount = Decimal("0")
        total_shares = Decimal("0")
        for bid in cls._bids(bidding_round, cache):
            total_amount += cls.get_bid_monthly_amount(bid, position, bidding_round)
            total_shares += (
                cls.get_product_size(bid.product, bidding_round, cache) * bid.quantity
            )
        if total_shares == 0:
            return Decimal("0")
        return total_amount / total_shares

    @classmethod
    def get_bidder_average_per_month(
        cls, bidding_round, position=None, *, cache: dict
    ) -> Decimal:
        if position is None:
            position = cls.get_default_position(bidding_round, cache)
        amounts = [
            cls.get_bid_monthly_amount(bid, position, bidding_round)
            for bid in cls._bids(bidding_round, cache)
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
    def get_recommended_level(cls, bidding_round, cache: dict) -> int:
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            return 2
        levels = max(1, min(3, bidding_round.bid_levels))
        for level in range(1, levels + 1):
            if (
                cls.get_coverage_percent(
                    bidding_round,
                    cls.get_level_position(level, bidding_round),
                    cache=cache,
                )
                >= RECOMMENDED_COVERAGE_PERCENT
            ):
                return level
        return levels

    @classmethod
    def get_coverage_status(cls, bidding_round, position=None, *, cache: dict) -> str:
        coverage = cls.get_coverage_percent(bidding_round, position, cache=cache)
        if coverage >= COVERAGE_STATUS_GREEN_PERCENT:
            return "green"
        if coverage >= COVERAGE_STATUS_YELLOW_PERCENT:
            return "yellow"
        return "red"

    @classmethod
    def build_levels_evaluation(cls, bidding_round, cache: dict) -> dict:
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
                        cache=cache,
                    )
                ),
                "coverage_percent": cls.get_coverage_percent(
                    bidding_round,
                    cls.get_level_position(level, bidding_round),
                    cache=cache,
                ),
                "coverage_status": cls.get_coverage_status(
                    bidding_round,
                    cls.get_level_position(level, bidding_round),
                    cache=cache,
                ),
                "bidder_average_per_month": str(
                    cls.get_bidder_average_per_month(
                        bidding_round,
                        cls.get_level_position(level, bidding_round),
                        cache=cache,
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
        for bid in cls._bids(bidding_round, cache):
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
        position = cls.get_default_position(bidding_round, cache)
        capacity_shares = cls.get_capacity_shares(bidding_round, cache)
        current_shares = cls.get_current_shares(bidding_round, cache)
        return {
            "bidding_procedure": bidding_round.bidding_procedure,
            "bid_levels": bidding_round.bid_levels,
            "recommended_level": cls.get_recommended_level(bidding_round, cache),
            "bid_range_position": float(position),
            "coverage_status": cls.get_coverage_status(
                bidding_round, position, cache=cache
            ),
            "target_per_year": str(cls.get_target_per_year(bidding_round)),
            "capacity_shares": str(capacity_shares),
            "current_shares": str(current_shares),
            "utilization_percent": cls.get_utilization_percent(
                capacity_shares, current_shares
            ),
            "coverage_percent": cls.get_coverage_percent(
                bidding_round, position, cache=cache
            ),
            "bidder_average_per_month": str(
                cls.get_bidder_average_per_month(bidding_round, position, cache=cache)
            ),
            "levels": cls.build_levels_evaluation(bidding_round, cache),
        }

    @classmethod
    def build_admin_evaluation(cls, bidding_round, cache, position=None) -> dict:
        if position is None:
            position = cls.get_default_position(bidding_round, cache)
        position = cls.clamp_position(position)
        bids = bidding_round.bids.select_related("member", "product")
        auto_renewed = (
            cls.get_auto_renewed_by_member(bidding_round, cache)
            if cls.are_auto_renewed_included(bidding_round, cache)
            else {}
        )
        data = {
            "bidding_procedure": bidding_round.bidding_procedure,
            "bid_levels": bidding_round.bid_levels,
            "round_product_type_id": bidding_round.product_type_id,
            "include_auto_renewed": bidding_round.include_auto_renewed,
            "auto_renewed_per_year": str(
                sum(
                    (entry["yearly_reference"] for entry in auto_renewed.values()),
                    Decimal("0"),
                )
            ),
            "auto_renewed": list(auto_renewed.values()),
            "extra_positions": cls.build_extra_positions(bidding_round, cache),
            "non_bidder_rate_per_share": str(
                cls.build_non_bidder_rate_per_share(bidding_round, cache)
            ),
            "bid_range_position": float(position),
            "recommended_level": cls.get_recommended_level(bidding_round, cache),
            "coverage_status": cls.get_coverage_status(
                bidding_round, position, cache=cache
            ),
            "levels": cls.build_levels_evaluation(bidding_round, cache),
            "target_per_year": str(cls.get_target_per_year(bidding_round)),
            "reached_per_year": str(
                cls.get_reached_per_year(bidding_round, position, cache=cache)
            ),
            "coverage_percent": cls.get_coverage_percent(
                bidding_round, position, cache=cache
            ),
            "average_bid_locked_at": (
                bidding_round.average_bid_locked_at.isoformat()
                if bidding_round.average_bid_locked_at
                else None
            ),
            "locked_bid_range_position": (
                str(bidding_round.locked_bid_range_position)
                if bidding_round.locked_bid_range_position is not None
                else None
            ),
            "locked_surcharge_percent": str(bidding_round.locked_surcharge_percent),
            "locked_surcharge_on_bids": bidding_round.locked_surcharge_on_bids,
            "locked_surcharge_on_average": bidding_round.locked_surcharge_on_average,
            "bidder_count": bids.count(),
            "unconfirmed_bid_count": bids.filter(admin_confirmed__isnull=True).count(),
            "bidder_average_per_month": str(
                cls.get_bidder_average_per_month(bidding_round, position, cache=cache)
            ),
            "bids": bids,
        }
        serialized = RoundResultsResponseSerializer(
            data, context={"position": position}
        ).data
        serialized["bids"] = sorted(
            serialized["bids"], key=lambda row: row["member_name"].lower()
        )
        return serialized

    @classmethod
    def _bids(cls, bidding_round, cache: dict):
        key = ("bidding_round_bids", bidding_round.id)
        if key not in cache:
            cache[key] = list(bidding_round.bids.select_related("product"))
        return cache[key]
