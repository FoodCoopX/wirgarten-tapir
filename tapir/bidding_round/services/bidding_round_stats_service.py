from decimal import Decimal

from tapir.associations.models import AssociationMembershipType
from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.bidding_round.config import TRAFFIC_LIGHT
from tapir.bidding_round.models import (
    BidItem,
    BiddingRoundCreatedSubscription,
    BiddingRoundProduct,
    BiddingRoundProductPrice,
)
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    PickupLocationCapability,
    ProductCapacity,
    Subscription,
)
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_association

TRAFFIC_LIGHT_POSITION_MIN = Decimal("0")
TRAFFIC_LIGHT_POSITION_MAX = Decimal("100")

# A simple round with several bid levels recommends the first level whose coverage
# reaches this share of the season target (matches the traffic_light yellow threshold).
RECOMMENDED_COVERAGE_PERCENT = 90


class BiddingRoundStatsService:
    @classmethod
    def get_level_position(cls, level: int) -> Decimal:
        """Position of a bid level on the 0/50/100 axis (level 1 -> 0, 3 -> 100)."""
        return Decimal(str((level - 1) * 50))

    @classmethod
    def build_recommended_level(
        cls,
        bidding_round,
        cache,
        membership_included_in_product_type=False,
    ) -> int:
        """
        First bid level whose coverage (bids + auto-renewal + extra positions) reaches
        RECOMMENDED_COVERAGE_PERCENT of the target; otherwise the last level. The traffic_light
        procedure always evaluates the middle level.
        """
        if bidding_round.bidding_procedure == TRAFFIC_LIGHT:
            return 2

        levels = max(1, min(3, bidding_round.bid_levels))
        for level in range(1, levels + 1):
            stats = cls.build_stats(
                bidding_round,
                cache=cache,
                traffic_light_position=cls.get_level_position(level),
            )
            extra_positions = cls.build_extra_positions(
                bidding_round,
                cache=cache,
                membership_included_in_product_type=membership_included_in_product_type,
            )
            extra_reached_per_year = sum(
                (
                    position["reached_per_year"]
                    for position in extra_positions.values()
                    if position["applicable"]
                ),
                Decimal("0"),
            )
            totals = cls.build_totals(
                stats, extra_reached_per_year=extra_reached_per_year
            )
            percent = totals["percent"]
            if percent is not None and percent >= RECOMMENDED_COVERAGE_PERCENT:
                return level
        return levels

    @classmethod
    def get_default_position(
        cls, bidding_round, cache, membership_included_in_product_type=False
    ) -> Decimal:
        """Effective position used for public stats and the average bid. When the
        average bid has been locked, the locked position is authoritative."""
        if bidding_round.average_bid_locked_at is not None:
            return cls.clamp_traffic_light_position(
                bidding_round.locked_traffic_light_position
            )
        if bidding_round.bidding_procedure == TRAFFIC_LIGHT:
            return Decimal("50")
        return cls.get_level_position(
            cls.build_recommended_level(
                bidding_round,
                cache=cache,
                membership_included_in_product_type=membership_included_in_product_type,
            )
        )

    @classmethod
    def get_surcharge_factor(cls, bidding_round) -> Decimal:
        if bidding_round.average_bid_locked_at is None:
            return Decimal("1")
        return Decimal("1") + Decimal(bidding_round.locked_surcharge_percent) / 100

    @classmethod
    def get_effective_amount(
        cls, bid_item, bidding_round, cache, position=None
    ) -> Decimal:
        """
        Effective amount of a bid item at a position on the 0/50/100 axis. Pass the
        already computed position to avoid recomputing the recommended level for every
        item. When the average bid is locked and the surcharge applies to bids, the
        locked surcharge is included (capped at the pain threshold for the traffic
        light).
        """
        if position is None:
            position = cls.get_default_position(bidding_round, cache=cache)
        amount = cls._get_amount_for_position(bid_item, position)
        if (
            bidding_round.average_bid_locked_at is not None
            and bidding_round.locked_surcharge_on_bids
        ):
            amount = cls._apply_surcharge_to_amount(amount, bid_item, bidding_round)
        return amount

    @classmethod
    def _apply_surcharge_to_amount(cls, amount, bid_item, bidding_round) -> Decimal:
        return cls._apply_surcharge_factor(
            amount,
            bid_item,
            bidding_round.bidding_procedure == TRAFFIC_LIGHT,
            cls.get_surcharge_factor(bidding_round),
        )

    @classmethod
    def _apply_surcharge_factor(
        cls, amount, bid_item, is_traffic_light: bool, factor
    ) -> Decimal:
        amount = amount * factor
        if is_traffic_light:
            amount = min(amount, cls._get_red_amount(bid_item))
        return amount

    @classmethod
    def _get_red_amount(cls, bid_item) -> Decimal:
        base = bid_item.amount_2
        if base is None:
            base = (
                bid_item.amount_1
                if bid_item.amount_1 is not None
                else bid_item.amount_3
            )
        return bid_item.amount_3 if bid_item.amount_3 is not None else base

    @classmethod
    def clamp_traffic_light_position(cls, position) -> Decimal:
        try:
            value = Decimal(str(position))
        except (TypeError, ValueError):
            value = Decimal("50")
        return min(max(value, TRAFFIC_LIGHT_POSITION_MIN), TRAFFIC_LIGHT_POSITION_MAX)

    @classmethod
    def build_stats(
        cls,
        bidding_round,
        cache,
        include_auto_renewed=None,
        traffic_light_position=50,
    ):
        traffic_light_position = cls.clamp_traffic_light_position(
            traffic_light_position
        )
        if include_auto_renewed is None:
            include_auto_renewed = bidding_round.include_auto_renewed

        auto_renewed_contributions = {}
        if include_auto_renewed:
            auto_renewed_contributions = cls._get_auto_renewed_contributions(
                bidding_round, cache=cache
            )

        results = []
        for round_product in bidding_round.products.select_related(
            "product_type"
        ).all():
            product_type_id = round_product.product_type_id
            target_per_year = cls._get_target_per_year(bidding_round, product_type_id)
            reached_per_year = cls._get_reached_per_year(
                bidding_round,
                round_product,
                traffic_light_position=traffic_light_position,
            )
            target_shares = cls._get_target_shares(bidding_round, product_type_id)
            reached_shares = cls._get_reached_shares(
                bidding_round, round_product, cache=cache
            )

            auto_contribution = auto_renewed_contributions.get(
                product_type_id, {"euro": Decimal("0"), "shares": Decimal("0")}
            )
            reached_per_year += auto_contribution["euro"]
            reached_shares += auto_contribution["shares"]

            percent = cls._get_percent(reached_per_year, target_per_year)
            shares_percent = cls._get_percent(reached_shares, target_shares)

            results.append(
                {
                    "product_type_id": product_type_id,
                    "product_type_name": round_product.product_type.name,
                    "target_per_year": target_per_year,
                    "reached_per_year": reached_per_year,
                    "percent": percent,
                    "deficit": cls._get_deficit(target_per_year, reached_per_year),
                    "traffic_light": cls._get_traffic_light(percent),
                    "target_shares": target_shares,
                    "reached_shares": reached_shares,
                    "shares_percent": shares_percent,
                    "shares_deficit": cls._get_deficit(target_shares, reached_shares),
                    "shares_traffic_light": cls._get_traffic_light(shares_percent),
                }
            )
        return results

    @classmethod
    def build_totals(cls, stats, extra_reached_per_year=Decimal("0")):
        target_per_year = sum(
            (entry.get("target_per_year") or Decimal("0") for entry in stats),
            Decimal("0"),
        )
        reached_per_year = (
            sum(
                (entry.get("reached_per_year") or Decimal("0") for entry in stats),
                Decimal("0"),
            )
            + extra_reached_per_year
        )
        target_shares = sum(
            (entry.get("target_shares") or Decimal("0") for entry in stats),
            Decimal("0"),
        )
        reached_shares = sum(
            (entry.get("reached_shares") or Decimal("0") for entry in stats),
            Decimal("0"),
        )
        percent = cls._get_percent(reached_per_year, target_per_year)
        shares_percent = cls._get_percent(reached_shares, target_shares)
        return {
            "target_per_year": target_per_year,
            "reached_per_year": reached_per_year,
            "percent": percent,
            "deficit": cls._get_deficit(target_per_year, reached_per_year),
            "traffic_light": cls._get_traffic_light(percent),
            "target_shares": target_shares,
            "reached_shares": reached_shares,
            "shares_percent": shares_percent,
            "shares_deficit": cls._get_deficit(target_shares, reached_shares),
            "shares_traffic_light": cls._get_traffic_light(shares_percent),
        }

    @classmethod
    def build_public_stats(cls, bidding_round, cache):
        return cls.build_stats(
            bidding_round,
            cache=cache,
            include_auto_renewed=False,
            traffic_light_position=cls.get_default_position(bidding_round, cache=cache),
        )

    @classmethod
    def build_average_bid(cls, bidding_round, cache) -> dict:
        product_type_ids = list(
            bidding_round.products.values_list("product_type_id", flat=True)
        )
        target_per_year = sum(
            (
                cls._get_target_per_year(bidding_round, product_type_id)
                for product_type_id in product_type_ids
            ),
            Decimal("0"),
        )
        capacity_shares = sum(
            (
                cls._get_target_shares(bidding_round, product_type_id)
                for product_type_id in product_type_ids
            ),
            Decimal("0"),
        )

        if bidding_round.average_bid_locked_at is not None:
            return {
                "target_per_year": target_per_year,
                "capacity_shares": capacity_shares,
                "amount_per_share_per_month": (
                    bidding_round.locked_average_bid_per_share_per_month
                ),
                "amount_per_share_per_year": (
                    bidding_round.locked_average_bid_per_share_per_year
                ),
            }

        # Share-weighted average of the submitted bids (per 1.0 share and month). If
        # there are no bids yet, fall back to the season target per capacity share.
        bid_euro_per_year = Decimal("0")
        bid_shares = Decimal("0")
        reference_date = bidding_round.growing_period.start_date
        effective_position = cls.get_default_position(bidding_round, cache=cache)
        for round_product in bidding_round.products.select_related(
            "product_type"
        ).all():
            for bid_item in BidItem.objects.filter(
                bid__round=bidding_round, round_product=round_product
            ):
                size = cls._get_product_size(
                    bid_item.product, reference_date, cache=cache
                )
                bid_euro_per_year += (
                    cls._get_amount_for_position(bid_item, effective_position)
                    * bid_item.quantity
                    * 12
                )
                bid_shares += size * bid_item.quantity

        if bid_shares > 0:
            amount_per_share_per_year = bid_euro_per_year / bid_shares
        elif capacity_shares > 0:
            amount_per_share_per_year = target_per_year / capacity_shares
        else:
            amount_per_share_per_year = None

        if amount_per_share_per_year is None:
            return {
                "target_per_year": target_per_year,
                "capacity_shares": capacity_shares,
                "amount_per_share_per_month": None,
                "amount_per_share_per_year": None,
            }

        return {
            "target_per_year": target_per_year,
            "capacity_shares": capacity_shares,
            "amount_per_share_per_month": (amount_per_share_per_year / 12).quantize(
                Decimal("0.01")
            ),
            "amount_per_share_per_year": amount_per_share_per_year.quantize(
                Decimal("0.01")
            ),
        }

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
        """
        Average bid per share (month/year) for the locked position and surcharge,
        mirroring the frontend's financing projection (surcharge capped at the pain
        threshold for the traffic light, non-bidder floor preserved).
        """
        position = cls.clamp_traffic_light_position(position)
        factor = Decimal("1") + Decimal(str(surcharge_percent or 0)) / 100
        is_traffic_light = bidding_round.bidding_procedure == TRAFFIC_LIGHT

        projection = cls.build_financing_projection(
            bidding_round,
            cache=cache,
            include_auto_renewed=bidding_round.include_auto_renewed,
        )
        levels = projection["levels"]
        base_bid_reached = cls._interpolate(
            levels["green"]["reached_per_year"],
            levels["yellow"]["reached_per_year"],
            levels["red"]["reached_per_year"],
            position,
        )

        if surcharge_on_bids:
            bid_reached = Decimal("0")
            for bid_item in BidItem.objects.filter(
                bid__round=bidding_round
            ).select_related("product"):
                amount = cls._apply_surcharge_factor(
                    cls._get_amount_for_position(bid_item, position),
                    bid_item,
                    is_traffic_light,
                    factor,
                )
                bid_reached += amount * bid_item.quantity * 12
        else:
            bid_reached = base_bid_reached

        bid_shares = projection["bid_shares"]
        bidder_average_per_month = (
            bid_reached / (bid_shares * 12) if bid_shares else Decimal("0")
        )

        target_per_year = projection["target_per_year"]
        other_fixed = (
            projection["membership_per_year"] + projection["delivery_charge_per_year"]
        )
        payer_shares = projection["auto_shares"] + projection["remaining_shares"]
        if target_per_year and payer_shares:
            base_average = (target_per_year - other_fixed - base_bid_reached) / (
                payer_shares * 12
            )
        else:
            base_average = Decimal("0")
        floor_enabled = projection["non_bidders_min_average"]
        if floor_enabled:
            base_average = max(base_average, bidder_average_per_month)

        red_average = levels["red"]["average_per_share_per_month"]
        average_per_share_per_month = base_average
        if surcharge_on_average:
            average_per_share_per_month = base_average * factor
            if is_traffic_light:
                average_per_share_per_month = min(
                    average_per_share_per_month, red_average
                )
        if floor_enabled:
            average_per_share_per_month = max(
                average_per_share_per_month, bidder_average_per_month
            )

        average_per_share_per_month = average_per_share_per_month.quantize(
            Decimal("0.01")
        )
        bidder_average_per_month = bidder_average_per_month.quantize(Decimal("0.01"))
        return {
            "amount_per_share_per_month": average_per_share_per_month,
            "amount_per_share_per_year": (average_per_share_per_month * 12).quantize(
                Decimal("0.01")
            ),
            "bidder_amount_per_share_per_month": bidder_average_per_month,
            "bidder_amount_per_share_per_year": (
                bidder_average_per_month * 12
            ).quantize(Decimal("0.01")),
        }

    @classmethod
    def _interpolate(cls, green, yellow, red, position) -> Decimal:
        if position <= 50:
            return green + (yellow - green) * (position / Decimal("50"))
        return yellow + (red - yellow) * ((position - Decimal("50")) / Decimal("50"))

    @classmethod
    def build_financing_projection(
        cls,
        bidding_round,
        cache,
        include_auto_renewed=True,
        membership_included_in_product_type=False,
    ) -> dict:
        """
        Data for the solidarity slider: the existing bids' reached amount and the
        average per-share amount at the three anchor levels, plus the fixed
        contributions and the share counts. The frontend interpolates between the
        anchors to show the dynamic average bid and the coverage at full capacity.
        """
        round_products = list(
            bidding_round.products.select_related("product_type").all()
        )
        product_type_ids = [
            round_product.product_type_id for round_product in round_products
        ]

        target_per_year = sum(
            (
                cls._get_target_per_year(bidding_round, product_type_id)
                for product_type_id in product_type_ids
            ),
            Decimal("0"),
        )
        capacity_shares = sum(
            (
                cls._get_target_shares(bidding_round, product_type_id)
                for product_type_id in product_type_ids
            ),
            Decimal("0"),
        )
        bid_shares = sum(
            (
                cls._get_reached_shares(bidding_round, round_product, cache=cache)
                for round_product in round_products
            ),
            Decimal("0"),
        )

        auto_renewed = (
            cls._get_auto_renewed_contributions(bidding_round, cache=cache)
            if include_auto_renewed
            else {}
        )
        auto_shares = sum(
            (contribution["shares"] for contribution in auto_renewed.values()),
            Decimal("0"),
        )
        auto_euro = sum(
            (contribution["euro"] for contribution in auto_renewed.values()),
            Decimal("0"),
        )

        extra_positions = cls.build_extra_positions(
            bidding_round,
            cache=cache,
            membership_included_in_product_type=membership_included_in_product_type,
        )
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
            reached_per_year = sum(
                (
                    cls._get_reached_per_year(
                        bidding_round, round_product, traffic_light_position=position
                    )
                    for round_product in round_products
                ),
                Decimal("0"),
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
            "non_bidders_min_average": get_parameter_value(
                ParameterKeys.BIDDING_ROUND_NON_BIDDERS_MIN_AVERAGE, cache=cache
            ),
            "membership_included_in_product_type": membership_included_in_product_type,
            "levels": {
                "green": build_level(Decimal("0")),
                "yellow": build_level(Decimal("50")),
                "red": build_level(Decimal("100")),
            },
        }

    @classmethod
    def _percent(cls, part: Decimal, whole: Decimal) -> float:
        if not whole:
            return 0.0
        return float(part / whole * 100)

    @classmethod
    def build_public_evaluation(cls, bidding_round, cache) -> dict:
        """
        Reduced projection for the public evaluation page: only the aggregated
        utilization and coverage percentages per anchor level, without the internal
        financing breakdown. Mirrors the frontend's coverage model (no surcharge).
        """
        projection = cls.build_financing_projection(
            bidding_round,
            cache=cache,
            include_auto_renewed=bidding_round.include_auto_renewed,
        )

        target_per_year = projection["target_per_year"]
        capacity_shares = projection["capacity_shares"]
        bid_shares = projection["bid_shares"]
        auto_shares = projection["auto_shares"]
        remaining_shares = projection["remaining_shares"]
        other_fixed = (
            projection["membership_per_year"] + projection["delivery_charge_per_year"]
        )

        current_shares = bid_shares + (
            auto_shares if bidding_round.include_auto_renewed else Decimal("0")
        )
        payer_shares = (
            auto_shares + remaining_shares
            if bidding_round.include_auto_renewed
            else remaining_shares
        )

        def build_level(level_data: dict) -> dict:
            reached_per_year = level_data["reached_per_year"]
            bidder_average_per_month = (
                reached_per_year / (bid_shares * 12) if bid_shares else Decimal("0")
            )
            if target_per_year and payer_shares:
                non_bidder_average_per_month = (
                    target_per_year - other_fixed - reached_per_year
                ) / (payer_shares * 12)
            else:
                non_bidder_average_per_month = Decimal("0")
            if projection["non_bidders_min_average"]:
                non_bidder_average_per_month = max(
                    non_bidder_average_per_month, bidder_average_per_month
                )
            auto_total = (
                auto_shares * non_bidder_average_per_month * 12
                if bidding_round.include_auto_renewed
                else Decimal("0")
            )
            current_total_per_year = reached_per_year + other_fixed + auto_total
            return {
                "reached_per_year": reached_per_year,
                "current_total_per_year": current_total_per_year,
                "current_coverage_percent": cls._percent(
                    current_total_per_year, target_per_year
                ),
                "bidder_average_per_month": bidder_average_per_month.quantize(
                    Decimal("0.01")
                ),
            }

        levels = projection["levels"]
        return {
            "bidding_procedure": bidding_round.bidding_procedure,
            "bid_levels": bidding_round.bid_levels,
            "recommended_level": cls.build_recommended_level(
                bidding_round, cache=cache
            ),
            "traffic_light_position": cls.get_default_position(
                bidding_round, cache=cache
            ),
            "target_per_year": target_per_year,
            "capacity_shares": capacity_shares,
            "current_shares": current_shares,
            "utilization_percent": cls._percent(current_shares, capacity_shares),
            "levels": {
                "green": build_level(levels["green"]),
                "yellow": build_level(levels["yellow"]),
                "red": build_level(levels["red"]),
            },
        }

    @classmethod
    def build_non_bidder_rate_per_share(
        cls, bidding_round, cache, bid_level: int | None = None
    ) -> Decimal | None:
        """
        Per-share monthly rate a non-bidder has to pay, including the non-bidder floor
        (max(bidders' average, derived average)) when enabled. When the average bid is
        locked, the locked average (including the locked surcharge) is returned.
        """
        if bidding_round.average_bid_locked_at is not None:
            return bidding_round.locked_average_bid_per_share_per_month

        if bid_level is None:
            bid_level = cls.build_recommended_level(bidding_round, cache=cache)

        projection = cls.build_financing_projection(
            bidding_round,
            cache=cache,
            include_auto_renewed=bidding_round.include_auto_renewed,
        )
        level = max(1, min(3, bid_level))
        key = ("green", "yellow", "red")[level - 1]
        if bidding_round.bidding_procedure == TRAFFIC_LIGHT:
            key = "yellow"
        level_data = projection["levels"][key]
        reached_per_year = level_data["reached_per_year"]
        bidder_average = level_data["average_per_share_per_month"]

        target_per_year = projection["target_per_year"]
        other_fixed = (
            projection["membership_per_year"] + projection["delivery_charge_per_year"]
        )
        auto_shares = projection["auto_shares"]
        remaining_shares = projection["remaining_shares"]
        payer_shares = (
            auto_shares + remaining_shares
            if bidding_round.include_auto_renewed
            else remaining_shares
        )
        if target_per_year and payer_shares:
            derived_average = (target_per_year - other_fixed - reached_per_year) / (
                payer_shares * 12
            )
        else:
            derived_average = Decimal("0")

        if projection["non_bidders_min_average"]:
            return max(derived_average, bidder_average)
        return derived_average

    @classmethod
    def build_extra_positions(
        cls, bidding_round, cache, membership_included_in_product_type=False
    ) -> dict:
        round_product = bidding_round.products.select_related("product_type").first()
        product_type = round_product.product_type if round_product is not None else None

        membership_position = cls._get_membership_position(bidding_round, cache)
        if membership_included_in_product_type:
            membership_position["applicable"] = False

        return {
            "membership": membership_position,
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

        bids_per_pickup_location = {}
        for bid in bidding_round.bids.all():
            if bid.pickup_location_id is None:
                continue
            bids_per_pickup_location[bid.pickup_location_id] = (
                bids_per_pickup_location.get(bid.pickup_location_id, 0) + 1
            )

        cache_key = (
            "bidding_round_delivery_charge_per_location",
            bidding_round.id,
            product_type.id,
        )
        charge_by_location = cache.get(cache_key)
        if charge_by_location is None:
            charge_by_location = {
                pickup_location_id: BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
                    pickup_location_id=pickup_location_id,
                    product_type=product_type,
                    growing_period=bidding_round.growing_period,
                    cache=cache,
                )
                for pickup_location_id in bids_per_pickup_location
            }
            cache[cache_key] = charge_by_location

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
    def build_results_table(cls, bidding_round, cache):
        bids = list(
            bidding_round.bids.select_related("member", "round")
            .prefetch_related(
                "items__product",
                "items__round_product__product_type",
                "pickup_location",
            )
            .all()
        )
        bids_by_member_id = {bid.member_id: bid for bid in bids}
        members = list(Member.objects.all())

        auto_renewed_by_member = {}
        if bidding_round.include_auto_renewed:
            auto_renewed_by_member = cls.get_auto_renewed_by_member(
                bidding_round, cache=cache
            )

        active_member_ids = set(bids_by_member_id.keys()) | set(
            auto_renewed_by_member.keys()
        )
        active_member_ids |= set(
            Subscription.objects.filter(
                period=bidding_round.growing_period,
                cancellation_ts__isnull=True,
            ).values_list("member_id", flat=True)
        )

        table = {
            "members": [
                {
                    "member": member,
                    "has_bid": member.id in bids_by_member_id,
                    "bid": bids_by_member_id.get(member.id),
                    "is_active_in_contract_period": member.id in active_member_ids,
                    "is_auto_renewed": member.id in auto_renewed_by_member,
                    "auto_renewed_items": (
                        auto_renewed_by_member[member.id]["items"]
                        if member.id in auto_renewed_by_member
                        else []
                    ),
                    "auto_renewed_pickup_location_name": (
                        auto_renewed_by_member[member.id]["pickup_location_name"]
                        if member.id in auto_renewed_by_member
                        else None
                    ),
                    "auto_renewed_amount_per_year": (
                        auto_renewed_by_member[member.id]["euro_per_year"]
                        if member.id in auto_renewed_by_member
                        else None
                    ),
                    "auto_renewed_amount_per_month": (
                        auto_renewed_by_member[member.id]["euro_per_month"]
                        if member.id in auto_renewed_by_member
                        else None
                    ),
                }
                for member in members
            ]
        }

        if BiddingRoundService.is_pickup_location_change_enabled(cache=cache):
            table["pickup_locations"] = cls._build_pickup_location_capacity(
                bidding_round,
                cache=cache,
                auto_renewed_by_member=auto_renewed_by_member,
            )

        return table

    @classmethod
    def get_auto_renewed_subscriptions(cls, bidding_round, cache) -> list:
        """
        The non-bidder subscriptions of the round: the subscriptions that will be
        renewed (before the contracts are created) plus the non-bidder contracts the
        round has already created. Creating the contracts materialises the renewals,
        so they no longer count as "will be renewed"; this keeps the evaluation stable
        before and after the contracts are created.
        """
        subscriptions = {}
        try:
            for (
                subscription
            ) in AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=bidding_round.growing_period.start_date,
                cache=cache,
            ):
                subscriptions[subscription.id] = subscription
        except KeyError:
            pass

        # Filter by growing period (not by round), because several rounds can share a
        # season and any of them may have materialised the renewals.
        created_subscription_ids = list(
            BiddingRoundCreatedSubscription.objects.filter(
                round__growing_period_id=bidding_round.growing_period_id,
                is_bidder_contract=False,
            ).values_list("subscription_id", flat=True)
        )
        for subscription in Subscription.objects.filter(
            id__in=created_subscription_ids
        ).select_related("product", "product__type"):
            subscriptions[subscription.id] = subscription

        return list(subscriptions.values())

    @classmethod
    def get_auto_renewed_by_member(cls, bidding_round, cache) -> dict:
        """Auto-renewed members without a bid, with the reference amount they
        would contribute (reference value per month/year), the renewed products and
        the pickup location that gets reserved for the new period."""
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        product_type_ids = set(
            bidding_round.products.values_list("product_type_id", flat=True)
        )
        subscriptions = cls.get_auto_renewed_subscriptions(bidding_round, cache)
        pickup_location_names = {
            pickup_location.id: pickup_location.name
            for pickup_location in PickupLocation.objects.all()
        }

        reference_date = bidding_round.growing_period.start_date
        result = {}
        for subscription in subscriptions:
            if subscription.member_id in bid_member_ids:
                continue
            if subscription.product.type_id not in product_type_ids:
                continue
            reference_value = cls.get_reference_value(
                bidding_round, subscription.product, cache=cache
            )
            size = cls._get_product_size(
                subscription.product, reference_date, cache=cache
            )
            entry = result.setdefault(
                subscription.member_id,
                {"euro_per_year": Decimal("0"), "shares": Decimal("0"), "items": []},
            )
            entry["euro_per_year"] += (
                reference_value * size * subscription.quantity * 12
            )
            entry["shares"] += size * subscription.quantity
            entry["items"].append(
                {
                    "product_type_name": subscription.product.type.name,
                    "product_name": subscription.product.name,
                    "quantity": subscription.quantity,
                }
            )
            if entry.get("pickup_location_id") is None:
                pickup_location_id = (
                    MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                        member_id=subscription.member_id,
                        reference_date=reference_date,
                        cache=cache,
                    )
                )
                entry["pickup_location_id"] = pickup_location_id
                entry["pickup_location_name"] = pickup_location_names.get(
                    pickup_location_id
                )
        for entry in result.values():
            entry["euro_per_month"] = entry["euro_per_year"] / 12
        return result

    @classmethod
    def _get_auto_renewed_contributions(cls, bidding_round, cache):
        product_type_ids = set(
            bidding_round.products.values_list("product_type_id", flat=True)
        )
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        subscriptions = cls.get_auto_renewed_subscriptions(bidding_round, cache)

        contributions = {}
        reference_date = bidding_round.growing_period.start_date
        for subscription in subscriptions:
            if subscription.member_id in bid_member_ids:
                continue
            if subscription.product.type_id not in product_type_ids:
                continue
            reference_value = cls.get_reference_value(
                bidding_round, subscription.product, cache=cache
            )
            size = cls._get_product_size(
                subscription.product, reference_date, cache=cache
            )
            product_type_id = subscription.product.type_id
            entry = contributions.setdefault(
                product_type_id, {"euro": Decimal("0"), "shares": Decimal("0")}
            )
            entry["euro"] += reference_value * size * subscription.quantity * 12
            entry["shares"] += size * subscription.quantity
        return contributions

    @classmethod
    def get_reference_value(cls, bidding_round, product, cache=None) -> Decimal:
        if cache is not None:
            cache_key = ("bidding_round_reference_values", bidding_round.id)
            reference_values = cache.get(cache_key)
            if reference_values is None:
                reference_values = {
                    price.product_id: price.reference_value
                    for price in BiddingRoundProductPrice.objects.filter(
                        round_product__round=bidding_round
                    )
                }
                cache[cache_key] = reference_values
            return reference_values.get(product.id) or Decimal("0")
        price = BiddingRoundProductPrice.objects.filter(
            round_product__round=bidding_round, product=product
        ).first()
        if price is None or price.reference_value is None:
            return Decimal("0")
        return price.reference_value

    @classmethod
    def _get_target_per_year(cls, bidding_round, product_type_id) -> Decimal:
        return sum(
            (
                round_product.target_amount_per_year or Decimal("0")
                for round_product in BiddingRoundProduct.objects.filter(
                    round=bidding_round, product_type_id=product_type_id
                )
            ),
            Decimal("0"),
        )

    @classmethod
    def _get_target_shares(cls, bidding_round, product_type_id) -> Decimal:
        return sum(
            (
                capacity.capacity or Decimal("0")
                for capacity in ProductCapacity.objects.filter(
                    period=bidding_round.growing_period,
                    product_type_id=product_type_id,
                )
            ),
            Decimal("0"),
        )

    @classmethod
    def _get_reached_per_year(
        cls, bidding_round, round_product, traffic_light_position=Decimal("50")
    ) -> Decimal:
        return sum(
            (
                cls._get_amount_for_position(bid_item, traffic_light_position)
                * bid_item.quantity
                * 12
                for bid_item in BidItem.objects.filter(
                    bid__round=bidding_round, round_product=round_product
                )
            ),
            Decimal("0"),
        )

    @classmethod
    def _get_amount_for_position(cls, bid_item, traffic_light_position) -> Decimal:
        """
        Amount of a bid item at a position on the 0/50/100 axis: 0 = amount_1 (green,
        wish), 50 = amount_2 (yellow, satisfied), 100 = amount_3 (red, pain
        threshold), interpolated in between.
        Missing levels fall back to the base level, so a simple round with fewer
        levels yields a constant amount and a simple round with several levels hits the
        exact level values at the positions 0/50/100.
        """
        position = cls.clamp_traffic_light_position(traffic_light_position)
        base = bid_item.amount_2
        if base is None:
            base = (
                bid_item.amount_1
                if bid_item.amount_1 is not None
                else bid_item.amount_3
            )
        green = bid_item.amount_1 if bid_item.amount_1 is not None else base
        yellow = bid_item.amount_2 if bid_item.amount_2 is not None else base
        red = bid_item.amount_3 if bid_item.amount_3 is not None else base
        if position <= 50:
            return green + (yellow - green) * (position / Decimal("50"))
        return yellow + (red - yellow) * ((position - Decimal("50")) / Decimal("50"))

    @classmethod
    def _get_reached_shares(cls, bidding_round, round_product, cache) -> Decimal:
        reference_date = bidding_round.growing_period.start_date
        return sum(
            (
                cls._get_product_size(bid_item.product, reference_date, cache=cache)
                * bid_item.quantity
                for bid_item in BidItem.objects.filter(
                    bid__round=bidding_round, round_product=round_product
                ).select_related("product")
            ),
            Decimal("0"),
        )

    @classmethod
    def _get_product_size(cls, product, reference_date, cache) -> Decimal:
        price = get_product_price(product, reference_date, cache=cache)
        return Decimal(price.size) if price is not None else Decimal("1")

    @classmethod
    def _get_percent(cls, reached, target):
        if not target or target <= 0:
            return None
        return float(reached / target * 100)

    @classmethod
    def _get_deficit(cls, target, reached):
        if target is not None and reached < target:
            return target - reached
        return None

    @classmethod
    def _get_traffic_light(cls, percent):
        if percent is None:
            return None
        if percent >= 100:
            return "green"
        if percent >= 90:
            return "yellow"
        return "red"

    @classmethod
    def _build_pickup_location_capacity(
        cls, bidding_round, cache, auto_renewed_by_member=None
    ):
        product_type_ids = list(
            bidding_round.products.values_list("product_type_id", flat=True)
        )
        bids = list(
            bidding_round.bids.prefetch_related(
                "items__product", "pickup_location"
            ).all()
        )
        reference_date = bidding_round.growing_period.start_date

        demand_by_location = {}
        for bid in bids:
            shares = sum(
                (
                    cls._get_product_size(item.product, reference_date, cache=cache)
                    * item.quantity
                    for item in bid.items.all()
                ),
                Decimal("0"),
            )
            if bid.pickup_location_id:
                demand_by_location[bid.pickup_location_id] = (
                    demand_by_location.get(bid.pickup_location_id, Decimal("0"))
                    + shares
                )

        if bidding_round.include_auto_renewed:
            if auto_renewed_by_member is None:
                auto_renewed_by_member = cls.get_auto_renewed_by_member(
                    bidding_round, cache=cache
                )
            for entry in auto_renewed_by_member.values():
                pickup_location_id = entry.get("pickup_location_id")
                if not pickup_location_id:
                    continue
                demand_by_location[pickup_location_id] = demand_by_location.get(
                    pickup_location_id, Decimal("0")
                ) + entry.get("shares", Decimal("0"))

        capacity_by_location = {}
        for capability in PickupLocationCapability.objects.filter(
            product_type_id__in=product_type_ids
        ):
            capacity_by_location[capability.pickup_location_id] = (
                capacity_by_location.get(capability.pickup_location_id, Decimal("0"))
                + (capability.max_capacity or Decimal("0"))
            )

        result = []
        for pickup_location in PickupLocation.objects.all():
            capacity = capacity_by_location.get(pickup_location.id, Decimal("0"))
            demand = demand_by_location.get(pickup_location.id, Decimal("0"))
            result.append(
                {
                    "pickup_location": pickup_location,
                    "capacity": capacity,
                    "demand": demand,
                    "fill_percent": (
                        float(demand / capacity * 100) if capacity else None
                    ),
                }
            )
        return result

    @classmethod
    def build_public_pickup_location_utilization(cls, bidding_round, cache) -> dict:
        """
        Per-depot utilization of the current bidding round, keyed by pickup location id.
        Demand is derived from the bids' wishes (primary + fallback), capacity from the
        depot capabilities for the round's product types. Aggregate only, safe to expose
        publicly. Cached per round within the request cache.
        """
        cache_key = f"public_pickup_location_utilization_{bidding_round.id}"
        if cache_key in cache:
            return cache[cache_key]

        result = {}
        for entry in cls._build_pickup_location_capacity(bidding_round, cache=cache):
            pickup_location = entry["pickup_location"]
            capacity = entry["capacity"]
            demand = entry["demand"]
            result[pickup_location.id] = {
                "capacity": str(capacity),
                "demand": str(demand),
                "fill_percent": entry["fill_percent"],
                "is_full": capacity > 0 and demand >= capacity,
            }
        cache[cache_key] = result
        return result
