from decimal import Decimal, InvalidOperation

from django.utils.translation import gettext_lazy as _

from tapir.associations.models import AssociationMembershipType
from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.bidding_round.config import BIDDING_ROUND_PROCEDURE_BID_RANGE
from tapir.bidding_round.models import (
    BidItem,
    BiddingRoundCreatedSubscription,
    BiddingRoundProductPrice,
)
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.bidding_round.services.bidding_round_contract_row_service import (
    BiddingRoundContractRowService,
)
from tapir.bidding_round.services.bidding_round_view_service import (
    BiddingRoundViewService,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    PickupLocationCapability,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_product_price
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
    def get_target_per_year(cls, bidding_round) -> Decimal:
        round_product_type = bidding_round.product_types.first()
        if round_product_type is None:
            return Decimal("0")
        return round_product_type.target_amount_per_year or Decimal("0")

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

    @classmethod
    def get_amount_for_position(cls, bid_item, position, bidding_round=None) -> Decimal:
        """Amount at a position on the 0/100 axis.

        The bid range interpolates linearly between green (0) and red (100).
        Simple rounds keep the 0/50/100 interpolation; missing levels fall back
        to the middle amount, so a one-amount round yields a constant value.
        """
        position = cls.clamp_position(position)
        if bidding_round is None:
            bidding_round = bid_item.bid.round
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            green = cls._first_amount(bid_item.amount_1, bid_item.amount_2)
            red = cls._first_amount(bid_item.amount_2, bid_item.amount_1)
            return green + (red - green) * position / Decimal("100")
        base = cls._first_amount(
            bid_item.amount_2, bid_item.amount_1, bid_item.amount_3
        )
        green = bid_item.amount_1 if bid_item.amount_1 is not None else base
        yellow = bid_item.amount_2 if bid_item.amount_2 is not None else base
        red = bid_item.amount_3 if bid_item.amount_3 is not None else base
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
        cls, amount, bid_item, bidding_round, factor, surcharge_on_bids
    ) -> Decimal:
        if not surcharge_on_bids:
            return amount
        amount = amount * factor
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            red = bid_item.amount_2 or bid_item.amount_1 or Decimal("0")
            amount = min(amount, red)
        return amount

    @classmethod
    def get_effective_amount(cls, bid_item, position, bidding_round=None) -> Decimal:
        amount = cls.get_amount_for_position(bid_item, position, bidding_round)
        if bidding_round is None:
            return amount
        return cls._apply_surcharge_and_cap(
            amount,
            bid_item,
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
        for item in cls._items(bidding_round, cache):
            amount = cls.get_amount_for_position(item, position, bidding_round)
            total_amount += (
                cls._apply_surcharge_and_cap(
                    amount,
                    item,
                    bidding_round,
                    factor,
                    bool(surcharge_on_bids),
                )
                * item.quantity
            )
            total_shares += (
                cls._get_size(item.product, bidding_round, cache) * item.quantity
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
        cls,
        bidding_round,
        position=None,
        *,
        cache: dict,
        include_auto_renewed: bool | None = None,
    ) -> Decimal:
        if position is None:
            position = cls.get_default_position(bidding_round, cache)
        total = cls._get_reached_per_year(bidding_round, position, cache)
        if include_auto_renewed is None:
            include_auto_renewed = cls.are_auto_renewed_included(bidding_round, cache)
        if include_auto_renewed:
            total += cls.get_auto_renewed_per_year(bidding_round, cache)
        return total

    @classmethod
    def _get_reached_per_year(cls, bidding_round, position, cache: dict) -> Decimal:
        """Bid-only reached amount of the round at a position, without auto-renewal."""
        return sum(
            (
                cls.get_effective_amount(item, position, bidding_round)
                * item.quantity
                * 12
                for item in cls._items(bidding_round, cache)
            ),
            Decimal("0"),
        )

    @classmethod
    def are_auto_renewed_included(cls, bidding_round, cache) -> bool:
        return bidding_round.include_auto_renewed

    @classmethod
    def get_product_size(cls, product, bidding_round, cache: dict) -> Decimal:
        cache_key = ("bidding_round_product_sizes", bidding_round.id)
        if cache_key not in cache:
            cache[cache_key] = {
                price.product_id: price.size
                for price in BiddingRoundProductPrice.objects.filter(
                    round_product_type__round=bidding_round
                )
            }
        size = cache[cache_key].get(product.id)
        if size is not None:
            return Decimal(size)
        product_price = get_product_price(
            product,
            reference_date=bidding_round.growing_period.start_date,
            cache=cache,
        )
        if product_price is not None and product_price.size:
            return Decimal(str(product_price.size))
        return Decimal("1")

    @classmethod
    def _get_size(cls, product, bidding_round, cache) -> Decimal:
        return cls.get_product_size(product, bidding_round, cache)

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
        for item in cls._items(bidding_round, cache):
            total_amount += (
                cls.get_effective_amount(item, position, bidding_round) * item.quantity
            )
            total_shares += (
                cls.get_product_size(item.product, bidding_round, cache) * item.quantity
            )
        if total_shares == 0:
            return Decimal("0")
        return total_amount / total_shares

    @classmethod
    def get_auto_renewed_subscriptions(cls, bidding_round, cache) -> list:
        """The non-bidder subscriptions of the round: the subscriptions that will be
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
        would contribute (month/year), the renewed products and the pickup
        location that gets reserved for the new period."""
        cache_key = ("bidding_round_auto_renewed", bidding_round.id)
        if cache_key in cache:
            return cache[cache_key]

        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        product_type_ids = set(
            bidding_round.product_types.values_list("product_type_id", flat=True)
        )
        subscriptions = cls.get_auto_renewed_subscriptions(bidding_round, cache)
        pickup_location_names = {
            pickup_location.id: pickup_location.name
            for pickup_location in PickupLocation.objects.all()
        }

        reference_date = bidding_round.growing_period.start_date
        rate = (
            cls.build_non_bidder_rate_per_share(bidding_round, cache)
            if bidding_round.average_bid_locked_at is not None
            else None
        )

        result = {}
        for subscription in subscriptions:
            if subscription.member_id in bid_member_ids:
                continue
            if subscription.product.type_id not in product_type_ids:
                continue
            reference_value = cls.get_reference_value(
                bidding_round, subscription.product, cache=cache
            )
            size = cls._get_size(subscription.product, bidding_round, cache)
            entry = result.setdefault(
                subscription.member_id,
                {
                    "member_id": subscription.member_id,
                    "member_name": str(subscription.member),
                    "member_email": subscription.member.email,
                    "euro_per_year": Decimal("0"),
                    "euro_per_month": Decimal("0"),
                    "shares": Decimal("0"),
                    "items": [],
                    "monthly_reference": Decimal("0"),
                    "yearly_reference": Decimal("0"),
                },
            )
            expected_rate = (
                Decimal("0")
                if subscription.price_override == 0
                else max(reference_value, rate or Decimal("0"))
            )
            entry["euro_per_year"] += expected_rate * size * subscription.quantity * 12
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
            entry["monthly_reference"] = entry["euro_per_month"]
            entry["yearly_reference"] = entry["euro_per_year"]

        cache[cache_key] = result
        return result

    @classmethod
    def get_auto_renewed_per_year(cls, bidding_round, cache) -> Decimal:
        return sum(
            (
                entry["euro_per_year"]
                for entry in cls.get_auto_renewed_by_member(
                    bidding_round, cache
                ).values()
            ),
            Decimal("0"),
        )

    @classmethod
    def _get_auto_renewed_contributions(cls, bidding_round, cache) -> dict:
        cache_key = ("bidding_round_auto_renewed_contributions", bidding_round.id)
        if cache_key in cache:
            return cache[cache_key]
        product_type_ids = set(
            bidding_round.product_types.values_list("product_type_id", flat=True)
        )
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        subscriptions = cls.get_auto_renewed_subscriptions(bidding_round, cache)

        rate = (
            cls.build_non_bidder_rate_per_share(bidding_round, cache)
            if bidding_round.average_bid_locked_at is not None
            else None
        )

        contributions = {}
        for subscription in subscriptions:
            if subscription.member_id in bid_member_ids:
                continue
            if subscription.product.type_id not in product_type_ids:
                continue
            reference_value = cls.get_reference_value(
                bidding_round, subscription.product, cache=cache
            )
            size = cls._get_size(subscription.product, bidding_round, cache)
            product_type_id = subscription.product.type_id
            entry = contributions.setdefault(
                product_type_id, {"euro": Decimal("0"), "shares": Decimal("0")}
            )
            expected_rate = (
                Decimal("0")
                if subscription.price_override == 0
                else max(reference_value, rate or Decimal("0"))
            )
            entry["euro"] += expected_rate * size * subscription.quantity * 12
            entry["shares"] += size * subscription.quantity
        cache[cache_key] = contributions
        return contributions

    @classmethod
    def get_reference_value(cls, bidding_round, product, cache: dict) -> Decimal:
        cache_key = ("bidding_round_reference_values", bidding_round.id)
        reference_values = cache.get(cache_key)
        if reference_values is None:
            reference_values = {
                price.product_id: price.reference_value
                for price in BiddingRoundProductPrice.objects.filter(
                    round_product_type__round=bidding_round
                )
            }
            cache[cache_key] = reference_values
        return reference_values.get(product.id) or Decimal("0")

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
        for item in cls._items(bidding_round, cache):
            total_amount += (
                cls.get_effective_amount(item, position, bidding_round) * item.quantity
            )
            total_shares += (
                cls._get_size(item.product, bidding_round, cache) * item.quantity
            )
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
        cache_key = ("bidding_round_extra_positions", bidding_round.id)
        if cache_key in cache:
            return cache[cache_key]
        round_product_type = bidding_round.product_types.select_related(
            "product_type"
        ).first()
        product_type = (
            round_product_type.product_type if round_product_type is not None else None
        )
        positions = {
            "membership": cls._get_membership_position(bidding_round, cache),
            "delivery_charge": cls._get_delivery_charge_position(
                bidding_round, product_type, cache
            ),
        }
        cache[cache_key] = positions
        return positions

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

        try:
            membership_fee_waived = get_parameter_value(
                key=ParameterKeys.ASSOCIATIONS_MEMBERSHIP_FEE_WAIVED_WITH_PRODUCTS,
                cache=cache,
            )
        except KeyError:
            membership_fee_waived = False
        if membership_fee_waived:
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
        cls,
        bidding_round,
        position=None,
        *,
        cache: dict,
        include_auto_renewed: bool | None = None,
    ) -> float:
        target = cls.get_target_per_year(bidding_round)
        if target == 0:
            return 0.0
        return float(
            cls.get_reached_per_year(
                bidding_round,
                position,
                include_auto_renewed=include_auto_renewed,
                cache=cache,
            )
            / target
            * 100
        )

    @classmethod
    def get_bidder_count(cls, bidding_round) -> int:
        return bidding_round.bids.count()

    @classmethod
    def get_bidder_average_per_month(
        cls, bidding_round, position=None, *, cache: dict
    ) -> Decimal:
        if position is None:
            position = cls.get_default_position(bidding_round, cache)
        amounts = [
            cls.get_item_monthly_amount(item, position, bidding_round)
            for item in cls._items(bidding_round, cache)
        ]
        if not amounts:
            return Decimal("0")
        return sum(amounts, Decimal("0")) / len(amounts)

    @classmethod
    def get_item_monthly_amount(
        cls, item, position=None, bidding_round=None
    ) -> Decimal:
        return cls.get_effective_amount(item, position, bidding_round) * item.quantity

    @classmethod
    def get_recommended_level(
        cls, bidding_round, cache: dict, include_auto_renewed: bool | None = None
    ) -> int:
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            return 2
        levels = max(1, min(3, bidding_round.bid_levels))
        for level in range(1, levels + 1):
            if (
                cls.get_coverage_percent(
                    bidding_round,
                    cls.get_level_position(level, bidding_round),
                    include_auto_renewed=include_auto_renewed,
                    cache=cache,
                )
                >= RECOMMENDED_COVERAGE_PERCENT
            ):
                return level
        return levels

    @classmethod
    def get_coverage_status(
        cls,
        bidding_round,
        position=None,
        *,
        cache: dict,
        include_auto_renewed: bool | None = None,
    ) -> str:
        coverage = cls.get_coverage_percent(
            bidding_round,
            position,
            include_auto_renewed=include_auto_renewed,
            cache=cache,
        )
        if coverage >= COVERAGE_STATUS_GREEN_PERCENT:
            return "green"
        if coverage >= COVERAGE_STATUS_YELLOW_PERCENT:
            return "yellow"
        return "red"

    @classmethod
    def build_levels_evaluation(
        cls, bidding_round, cache: dict, include_auto_renewed: bool | None = None
    ) -> dict:
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
                        include_auto_renewed=include_auto_renewed,
                        cache=cache,
                    )
                ),
                "coverage_percent": cls.get_coverage_percent(
                    bidding_round,
                    cls.get_level_position(level, bidding_round),
                    include_auto_renewed=include_auto_renewed,
                    cache=cache,
                ),
                "coverage_status": cls.get_coverage_status(
                    bidding_round,
                    cls.get_level_position(level, bidding_round),
                    include_auto_renewed=include_auto_renewed,
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
        round_product_type = bidding_round.product_types.first()
        if round_product_type is None:
            return Decimal("0")
        capacity = TapirCache.get_product_type_capacity_at_date(
            cache=cache,
            product_type=round_product_type.product_type,
            reference_date=bidding_round.growing_period.start_date,
        )
        if capacity is None or capacity.capacity is None:
            return Decimal("0")
        return Decimal(capacity.capacity).quantize(Decimal("0.01"))

    @classmethod
    def get_capacity_exceeded_errors(cls, bidding_round, cache) -> list[str]:
        """Reasons why the bids and auto-renewals do not fit the share or pickup
        location capacities. An empty list means everything fits."""
        errors = []
        projection = cls.build_financing_projection(
            bidding_round,
            cache,
            include_auto_renewed=bidding_round.include_auto_renewed,
        )
        capacity_shares = projection["capacity_shares"]
        required_shares = projection["bid_shares"] + projection["auto_shares"]
        if capacity_shares > 0 and required_shares > capacity_shares:
            errors.append(
                _(
                    "Die Gebote und Auto-Verlängerungen benötigen %(required)s Anteile, verfügbar sind %(capacity)s."
                )
                % {"required": required_shares, "capacity": capacity_shares}
            )
        for entry in cls._build_pickup_location_capacity(bidding_round, cache=cache):
            if entry["capacity"] > 0 and entry["demand"] > entry["capacity"]:
                errors.append(
                    _(
                        "Der Abholort %(name)s ist überlastet: %(demand)s von %(capacity)s Anteilen."
                    )
                    % {
                        "name": entry["pickup_location"].name,
                        "demand": entry["demand"],
                        "capacity": entry["capacity"],
                    }
                )
        return errors

    @classmethod
    def _get_target_shares(cls, bidding_round, cache) -> Decimal:
        return cls.get_capacity_shares(bidding_round, cache)

    @classmethod
    def get_current_shares(cls, bidding_round, cache) -> Decimal:
        total = Decimal("0")
        for item in cls._items(bidding_round, cache):
            total += cls._get_size(item.product, bidding_round, cache) * item.quantity
        return total

    @classmethod
    def _get_reached_shares(cls, bidding_round, cache) -> Decimal:
        return cls.get_current_shares(bidding_round, cache)

    @classmethod
    def get_utilization_percent(cls, capacity, current) -> float:
        if capacity == 0:
            return 0.0
        return float(current / capacity * 100)

    @classmethod
    def _get_percent(cls, part, whole):
        if not whole or whole <= 0:
            return None
        return float(part / whole * 100)

    @classmethod
    def _get_deficit(cls, target, reached):
        if target is not None and reached < target:
            return target - reached
        return None

    @classmethod
    def _get_coverage_status(cls, percent):
        if percent is None:
            return None
        if percent >= 100:
            return "green"
        if percent >= 90:
            return "yellow"
        return "red"

    @classmethod
    def _interpolate(cls, green, yellow, red, position) -> Decimal:
        if position <= 50:
            return green + (yellow - green) * (position / Decimal("50"))
        return yellow + (red - yellow) * ((position - Decimal("50")) / Decimal("50"))

    @classmethod
    def _get_amount_for_position(cls, bid_item, position) -> Decimal:
        return cls.get_amount_for_position(bid_item, position)

    @classmethod
    def build_stats(
        cls,
        bidding_round,
        cache,
        include_auto_renewed=None,
        bid_range_position=50,
    ) -> list:
        bid_range_position = cls.clamp_position(bid_range_position)
        if include_auto_renewed is None:
            include_auto_renewed = bidding_round.include_auto_renewed

        auto_renewed_contributions = {}
        if include_auto_renewed:
            auto_renewed_contributions = cls._get_auto_renewed_contributions(
                bidding_round, cache=cache
            )

        results = []
        for round_product_type in bidding_round.product_types.select_related(
            "product_type"
        ).all():
            product_type_id = round_product_type.product_type_id
            target_per_year = cls.get_target_per_year(bidding_round)
            reached_per_year = cls._get_reached_per_year(
                bidding_round, bid_range_position, cache
            )
            target_shares = cls._get_target_shares(bidding_round, cache)
            reached_shares = cls._get_reached_shares(bidding_round, cache)

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
                    "product_type_name": round_product_type.product_type.name,
                    "target_per_year": target_per_year,
                    "reached_per_year": reached_per_year,
                    "percent": percent,
                    "deficit": cls._get_deficit(target_per_year, reached_per_year),
                    "coverage_status": cls._get_coverage_status(percent),
                    "target_shares": target_shares,
                    "reached_shares": reached_shares,
                    "shares_percent": shares_percent,
                    "shares_deficit": cls._get_deficit(target_shares, reached_shares),
                    "shares_coverage_status": cls._get_coverage_status(shares_percent),
                }
            )
        return results

    @classmethod
    def build_totals(cls, stats, extra_reached_per_year=Decimal("0")) -> dict:
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
            "coverage_status": cls._get_coverage_status(percent),
            "target_shares": target_shares,
            "reached_shares": reached_shares,
            "shares_percent": shares_percent,
            "shares_deficit": cls._get_deficit(target_shares, reached_shares),
            "shares_coverage_status": cls._get_coverage_status(shares_percent),
        }

    @classmethod
    def build_financing_projection(
        cls, bidding_round, cache, include_auto_renewed=True
    ) -> dict:
        """Data for the solidarity slider: the existing bids' reached amount and the
        average per-share amount at the anchor levels (green/red for the bid range,
        green/yellow/red for simple rounds), plus the fixed contributions and the
        share counts. The frontend interpolates between the anchors to show the
        dynamic average bid and the coverage at full capacity.
        """
        target_per_year = cls.get_target_per_year(bidding_round)
        capacity_shares = cls.get_capacity_shares(bidding_round, cache)
        bid_shares = cls._get_reached_shares(bidding_round, cache)

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
            reached_per_year = cls._get_reached_per_year(bidding_round, position, cache)
            average_per_share_per_month = (
                reached_per_year / (bid_shares * 12) if bid_shares else Decimal("0")
            )
            return {
                "reached_per_year": reached_per_year,
                "average_per_share_per_month": average_per_share_per_month.quantize(
                    Decimal("0.01")
                ),
            }

        levels = {
            "green": build_level(Decimal("0")),
            "red": build_level(Decimal("100")),
        }
        if bidding_round.bidding_procedure != BIDDING_ROUND_PROCEDURE_BID_RANGE:
            levels = {
                "green": levels["green"],
                "yellow": build_level(Decimal("50")),
                "red": levels["red"],
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
            "levels": levels,
        }

    @classmethod
    def build_average_bid(cls, bidding_round, cache) -> dict:
        target_per_year = cls.get_target_per_year(bidding_round)
        capacity_shares = cls.get_capacity_shares(bidding_round, cache)

        if bidding_round.average_bid_locked_at is not None:
            amount_per_share_per_month = (
                bidding_round.locked_bidder_average_per_share_per_month
            )
            return {
                "target_per_year": target_per_year,
                "capacity_shares": capacity_shares,
                "amount_per_share_per_month": amount_per_share_per_month,
                "amount_per_share_per_year": (
                    (amount_per_share_per_month * 12).quantize(Decimal("0.01"))
                    if amount_per_share_per_month is not None
                    else None
                ),
            }

        # Share-weighted average of the submitted bids (per 1.0 share and month). If
        # there are no bids yet, fall back to the season target per capacity share.
        bid_euro_per_year = Decimal("0")
        bid_shares = Decimal("0")
        effective_position = cls.get_default_position(bidding_round, cache=cache)
        for bid_item in cls._items(bidding_round, cache):
            size = cls._get_size(bid_item.product, bidding_round, cache)
            bid_euro_per_year += (
                cls.get_amount_for_position(bid_item, effective_position)
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
    def build_results_table(
        cls,
        bidding_round,
        cache,
        bids_by_member_id=None,
        serialized_bids_by_member_id=None,
        filter_="all",
        sort="name",
    ) -> dict:
        if bids_by_member_id is None:
            bids = list(
                bidding_round.bids.select_related("member", "round__growing_period")
                .prefetch_related(
                    "items__product",
                    "items__round_product_type__product_type",
                )
                .all()
            )
            bids_by_member_id = {bid.member_id: bid for bid in bids}
        else:
            bids = list(bids_by_member_id.values())
        if serialized_bids_by_member_id is None:
            serialized_bids_by_member_id = {}

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

        member_ids = cls._get_member_ids_for_filter(
            filter_, active_member_ids, bids_by_member_id, auto_renewed_by_member
        )
        members = (
            Member.objects.all()
            if member_ids is None
            else Member.objects.filter(id__in=member_ids)
        )

        entries = [
            {
                "member": member,
                "member_id": member.id,
                "member_name": f"{member.first_name} {member.last_name}",
                "has_bid": member.id in bids_by_member_id,
                "bid": serialized_bids_by_member_id.get(member.id),
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
        entries = BiddingRoundViewService.filter_and_sort_members(
            entries, filter_, sort
        )

        return {
            "members": entries,
            "pickup_locations": cls._build_pickup_location_capacity(
                bidding_round,
                cache=cache,
                auto_renewed_by_member=auto_renewed_by_member,
                bids=bids,
            ),
        }

    @classmethod
    def _get_member_ids_for_filter(
        cls, filter_, active_member_ids, bids_by_member_id, auto_renewed_by_member
    ):
        if filter_ == "active_in_contract_period":
            return active_member_ids
        if filter_ == "has_bid":
            return set(bids_by_member_id)
        if filter_ == "auto_renewed":
            return set(auto_renewed_by_member)
        if filter_ == "no_bid":
            return active_member_ids - set(bids_by_member_id)
        return None

    @classmethod
    def _build_pickup_location_capacity(
        cls, bidding_round, cache, auto_renewed_by_member=None, bids=None
    ) -> list:
        cache_key = ("bidding_round_pickup_capacity", bidding_round.id)
        if cache_key in cache:
            return cache[cache_key]
        product_type_ids = list(
            bidding_round.product_types.values_list("product_type_id", flat=True)
        )
        if bids is None:
            bids = list(bidding_round.bids.prefetch_related("items__product").all())

        demand_by_location = cls._build_demand_by_location(bids, bidding_round, cache)
        cls._add_auto_renewed_demand(
            demand_by_location,
            bidding_round,
            auto_renewed_by_member,
            cache,
        )
        capacity_by_location = cls._build_capacity_by_location(product_type_ids)
        result = cls._build_capacity_rows(demand_by_location, capacity_by_location)
        cache[cache_key] = result
        return result

    @classmethod
    def _build_demand_by_location(cls, bids, bidding_round, cache) -> dict:
        reference_date = bidding_round.growing_period.start_date
        demand_by_location = {}
        for bid in bids:
            shares = sum(
                (
                    cls._get_size(item.product, bidding_round, cache) * item.quantity
                    for item in bid.items.all()
                ),
                Decimal("0"),
            )
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=bid.member_id,
                    reference_date=reference_date,
                    cache=cache,
                )
            )
            if pickup_location_id:
                demand_by_location[pickup_location_id] = (
                    demand_by_location.get(pickup_location_id, Decimal("0")) + shares
                )
        return demand_by_location

    @classmethod
    def _add_auto_renewed_demand(
        cls, demand_by_location, bidding_round, auto_renewed_by_member, cache
    ) -> None:
        if not bidding_round.include_auto_renewed:
            return
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

    @staticmethod
    def _build_capacity_by_location(product_type_ids) -> dict:
        capacity_by_location = {}
        for capability in PickupLocationCapability.objects.filter(
            product_type_id__in=product_type_ids
        ):
            capacity_by_location[capability.pickup_location_id] = (
                capacity_by_location.get(capability.pickup_location_id, Decimal("0"))
                + (capability.max_capacity or Decimal("0"))
            )
        return capacity_by_location

    @staticmethod
    def _build_capacity_rows(demand_by_location, capacity_by_location) -> list:
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
        """Per-depot utilization of the current bidding round, keyed by pickup location
        id. Demand is derived from the bids' wishes and auto-renewed shares, capacity
        from the depot capabilities for the round's product type. Aggregate only, safe
        to expose publicly. Cached per round within the request cache.
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
    def _serialize_results_table_members(
        cls, results_table, position=None, *, cache: dict
    ) -> list:
        members = []
        for entry in results_table["members"]:
            member = entry["member"]
            members.append(
                {
                    "member_id": member.id,
                    "member_name": f"{member.first_name} {member.last_name}",
                    "member_email": member.email,
                    "has_bid": entry["has_bid"],
                    "is_active_in_contract_period": entry[
                        "is_active_in_contract_period"
                    ],
                    "is_auto_renewed": entry["is_auto_renewed"],
                    "auto_renewed_items": entry["auto_renewed_items"],
                    "auto_renewed_pickup_location_name": entry[
                        "auto_renewed_pickup_location_name"
                    ],
                    "auto_renewed_amount_per_year": (
                        str(entry["auto_renewed_amount_per_year"])
                        if entry["auto_renewed_amount_per_year"] is not None
                        else None
                    ),
                    "auto_renewed_amount_per_month": (
                        str(entry["auto_renewed_amount_per_month"])
                        if entry["auto_renewed_amount_per_month"] is not None
                        else None
                    ),
                    "bid": entry["bid"],
                }
            )
        return members

    @classmethod
    def _serialize_results_table_pickup_locations(cls, results_table) -> list:
        return [
            {
                "pickup_location_id": entry["pickup_location"].id,
                "pickup_location_name": entry["pickup_location"].name,
                "capacity": str(entry["capacity"]),
                "demand": str(entry["demand"]),
                "fill_percent": entry["fill_percent"],
            }
            for entry in results_table.get("pickup_locations", [])
        ]

    @classmethod
    def build_admin_evaluation(
        cls,
        bidding_round,
        cache,
        position=None,
        include_auto_renewed=None,
        bid_range_position=None,
        filter_="all",
        sort="name",
    ) -> dict:
        if include_auto_renewed is None:
            include_auto_renewed = bidding_round.include_auto_renewed
        if bid_range_position is not None:
            position = bid_range_position
        if position is None:
            position = cls.get_default_position(bidding_round, cache)
        position = cls.clamp_position(position)
        default_position = cls.get_default_position(bidding_round, cache)

        stats = cls.build_stats(
            bidding_round,
            cache=cache,
            include_auto_renewed=include_auto_renewed,
            bid_range_position=position,
        )
        extra_positions = cls.build_extra_positions(bidding_round, cache)
        extra_reached_per_year = sum(
            (
                extra_position["reached_per_year"]
                for extra_position in extra_positions.values()
                if extra_position["applicable"]
            ),
            Decimal("0"),
        )
        totals = cls.build_totals(stats, extra_reached_per_year=extra_reached_per_year)

        auto_renewed = (
            cls.get_auto_renewed_by_member(bidding_round, cache)
            if include_auto_renewed
            else {}
        )

        bids = list(
            bidding_round.bids.select_related("member", "round__growing_period")
            .prefetch_related(
                "items__product",
                "items__round_product_type__product_type",
            )
            .all()
        )
        bids_by_member_id = {bid.member_id: bid for bid in bids}
        serialized_bids_by_member_id = {}
        rows = []
        for bid in bids:
            serialized = BiddingRoundViewService.serialize_bid(
                bid, effective_position=position, cache=cache
            )
            serialized_bids_by_member_id[bid.member_id] = serialized
            rows.append(
                {
                    "bid_id": bid.id,
                    "member_id": bid.member_id,
                    "member_name": str(bid.member),
                    "email": bid.member.email,
                    "pickup_location_name": serialized["pickup_location_name"],
                    "entered_by_admin": bid.entered_by_admin,
                    "admin_confirmed": (
                        bid.admin_confirmed.isoformat() if bid.admin_confirmed else None
                    ),
                    "updated_at": (
                        bid.updated_at.isoformat() if bid.updated_at else None
                    ),
                    "effective_amount": serialized["effective_amount"],
                    "amount_per_month": serialized["effective_amount"],
                    "amount_per_year": serialized["total_per_year"],
                    "items": serialized["items"],
                }
            )
        rows.sort(key=lambda row: row["member_name"].lower())

        results_table = cls.build_results_table(
            bidding_round,
            cache,
            bids_by_member_id=bids_by_member_id,
            serialized_bids_by_member_id=serialized_bids_by_member_id,
            filter_=filter_,
            sort=sort,
        )
        serialized_table = {
            "members": cls._serialize_results_table_members(
                results_table, position, cache=cache
            ),
            "pickup_locations": cls._serialize_results_table_pickup_locations(
                results_table
            ),
        }

        stats = [
            cls._stringify_mapping(entry, cls.STATS_AMOUNT_KEYS) for entry in stats
        ]
        totals = cls._stringify_mapping(totals, cls.STATS_AMOUNT_KEYS)
        extra_positions = {
            key: {
                **position_entry,
                "reached_per_year": str(position_entry["reached_per_year"]),
            }
            for key, position_entry in extra_positions.items()
        }
        auto_renewed_per_year_value = (
            sum(
                (entry["euro_per_year"] for entry in auto_renewed.values()),
                Decimal("0"),
            )
            if include_auto_renewed
            else Decimal("0")
        )
        reachable_per_year = (
            cls._get_reached_per_year(bidding_round, position, cache)
            + auto_renewed_per_year_value
        )
        auto_renewed = {
            member_id: cls._stringify_mapping(entry, cls.AUTO_RENEWED_AMOUNT_KEYS)
            for member_id, entry in auto_renewed.items()
        }
        average_bid = cls._stringify_mapping(
            cls.build_average_bid(bidding_round, cache), cls.AVERAGE_BID_KEYS
        )
        financing_projection = cls._stringify_mapping(
            cls.build_financing_projection(
                bidding_round,
                cache=cache,
                include_auto_renewed=include_auto_renewed,
            ),
            cls.FINANCING_PROJECTION_AMOUNT_KEYS,
        )
        contracts = [
            cls._stringify_mapping(row, cls.CONTRACT_AMOUNT_KEYS)
            for row in BiddingRoundContractRowService.serialize_contracts(
                bidding_round,
                cache,
                position=default_position,
                bids_by_member_id=bids_by_member_id,
            )
        ]

        round_product_type = bidding_round.product_types.first()
        return {
            "display_name": BiddingRoundViewService.get_display_name(cache),
            "bidding_procedure": bidding_round.bidding_procedure,
            "bid_levels": bidding_round.bid_levels,
            "round_product_type_id": (
                round_product_type.id if round_product_type is not None else None
            ),
            "include_auto_renewed": include_auto_renewed,
            "auto_renewed_enabled": (
                bidding_round.include_auto_renewed
                and BiddingRoundViewService.is_auto_renewal_enabled(cache)
            ),
            "auto_renewed_per_year": str(auto_renewed_per_year_value),
            "auto_renewed": list(auto_renewed.values()),
            "extra_positions": extra_positions,
            "stats": stats,
            "totals": totals,
            "average_bid": average_bid,
            "financing_projection": financing_projection,
            "results_table": serialized_table,
            "biddable_product": BiddingRoundViewService.build_biddable_product(
                bidding_round, cache
            ),
            "pickup_locations": BiddingRoundViewService.build_pickup_locations(
                bidding_round, cache
            ),
            "bid_options": BiddingRoundViewService.build_bid_options(cache),
            "non_bidder_rate_per_share": str(
                cls.build_non_bidder_rate_per_share(bidding_round, cache)
            ),
            "bid_range_position": float(position),
            "recommended_level": cls.get_recommended_level(
                bidding_round, cache, include_auto_renewed
            ),
            "coverage_status": cls.get_coverage_status(
                bidding_round,
                position,
                include_auto_renewed=include_auto_renewed,
                cache=cache,
            ),
            "levels": cls.build_levels_evaluation(
                bidding_round, cache, include_auto_renewed
            ),
            "target_per_year": str(cls.get_target_per_year(bidding_round)),
            "reached_per_year": str(reachable_per_year),
            "coverage_percent": cls.get_coverage_percent(
                bidding_round,
                position,
                include_auto_renewed=include_auto_renewed,
                cache=cache,
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
            "bidder_count": cls.get_bidder_count(bidding_round),
            "unconfirmed_bid_count": bidding_round.bids.filter(
                admin_confirmed__isnull=True
            ).count(),
            "bidder_average_per_month": str(
                cls.get_bidder_average_per_month(bidding_round, position, cache=cache)
            ),
            "bids": rows,
            "contracts_created_at": (
                bidding_round.contracts_created_at.isoformat()
                if bidding_round.contracts_created_at
                else None
            ),
            "growing_period_id": bidding_round.growing_period_id,
            "contracts": contracts,
            **BiddingRoundViewService.serialize_rollback_flags(bidding_round),
        }

    STATS_AMOUNT_KEYS = (
        "target_per_year",
        "reached_per_year",
        "deficit",
        "target_shares",
        "reached_shares",
        "shares_deficit",
    )
    AUTO_RENEWED_AMOUNT_KEYS = (
        "euro_per_year",
        "euro_per_month",
        "shares",
        "monthly_reference",
        "yearly_reference",
    )
    AVERAGE_BID_KEYS = (
        "target_per_year",
        "capacity_shares",
        "amount_per_share_per_month",
        "amount_per_share_per_year",
    )
    FINANCING_PROJECTION_AMOUNT_KEYS = (
        "target_per_year",
        "capacity_shares",
        "bid_shares",
        "auto_shares",
        "remaining_shares",
        "fixed_per_year",
        "auto_renew_per_year",
        "membership_per_year",
        "delivery_charge_per_year",
    )
    CONTRACT_AMOUNT_KEYS = (
        "standard_amount_per_month",
        "standard_amount_per_year",
        "contribution_amount_per_month",
        "contribution_amount_per_year",
        "amount_per_month",
        "amount_per_year",
        "bid_effective_amount",
        "non_bidder_floor_per_month",
        "previous_amount_per_month",
    )

    @staticmethod
    def _stringify_mapping(mapping, keys) -> dict:
        return {
            key: (None if value is None else (str(value) if key in keys else value))
            for key, value in mapping.items()
        }

    @classmethod
    def _items(cls, bidding_round, cache: dict):
        queryset = BidItem.objects.filter(bid__round=bidding_round).select_related(
            "product", "round_product_type__product_type"
        )
        key = ("bidding_round_items", bidding_round.id)
        if key not in cache:
            cache[key] = list(queryset)
        return cache[key]
