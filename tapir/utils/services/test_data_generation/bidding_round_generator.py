import datetime
import math
import random
from decimal import Decimal

from tapir.bidding_round.config import SIMPLE, TRAFFIC_LIGHT
from tapir.bidding_round.models import (
    Bid,
    BidItem,
    BiddingRoundProduct,
    BiddingRoundProductPrice,
)
from tapir.bidding_round.services.bidding_round_capacity_service import (
    BiddingRoundCapacityService,
)
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.vierlande_generator import (
    VierlandeGenerator,
)
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    PickupLocation,
    PickupLocationCapability,
    Product,
    ProductCapacity,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_product_price,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.utils import get_now, get_today

HARVEST_SHARE_PRODUCT_TYPE_NAME = "Ernteanteile"

REFERENCE_VALUE = Decimal("80.00")
MIN_AMOUNT = Decimal("60.00")
TARGET_AMOUNT_PER_YEAR = Decimal("220800.00")
GREEN_TARGET_RATIO = Decimal("0.81")
YELLOW_TARGET_RATIO = Decimal("0.91")
RED_TARGET_RATIO = Decimal("1.09")
SHARES_TARGET_RATIO = Decimal("0.90")
AUTO_RENEW_SHARES_RATIO = Decimal("0.20")


def _choose_sizes(sizes, number_of_bidders, target_total_size):
    """
    Distribute the bidders over the available variants (two adjacent sizes) so
    that the total number of shares is close to target_total_size.
    """
    unique_sizes = sorted(set(sizes))
    if number_of_bidders == 0 or not unique_sizes:
        return []
    average = target_total_size / number_of_bidders
    lower = max(
        (size for size in unique_sizes if size <= average), default=unique_sizes[0]
    )
    upper = min(
        (size for size in unique_sizes if size >= average), default=unique_sizes[-1]
    )
    if lower == upper:
        return [lower] * number_of_bidders
    upper_count = int(
        round((target_total_size - number_of_bidders * lower) / (upper - lower))
    )
    upper_count = max(0, min(number_of_bidders, upper_count))
    return [upper] * upper_count + [lower] * (number_of_bidders - upper_count)


class BiddingRoundGenerator:
    @classmethod
    def generate_bidding_round(cls, cache=None, organization=None):
        cache = cache or {}

        TapirParameter.objects.filter(key=ParameterKeys.BIDDING_ROUND_ENABLED).update(
            value="true"
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_URL_ENABLED
        ).update(value="true")
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")

        today = get_today(cache=cache)
        now = get_now(cache=cache)
        next_period = (
            GrowingPeriod.objects.filter(start_date__gt=today)
            .order_by("start_date")
            .first()
        )
        if next_period is None:
            next_period = GrowingPeriod.objects.order_by("start_date").last()

        harvest_share_product_type = ProductType.objects.filter(
            name=HARVEST_SHARE_PRODUCT_TYPE_NAME
        ).first()
        if harvest_share_product_type is None:
            return None

        capacities = list(
            ProductCapacity.objects.filter(
                period=next_period, product_type=harvest_share_product_type
            ).select_related("product_type")
        )
        if not capacities:
            return None

        end_at = now + datetime.timedelta(days=30)
        # Four demo rounds for the same season:
        #  - "traffic light": evaluated after the fact, green/satisfied/red.
        #  - "simple": simple round with a single bid (the yellow amount).
        #  - "simple - 3 bids": simple round with three bid levels
        #    (green/yellow/red amounts).
        #  - "capacity test": simple round whose bids deliberately fill the harvest
        #    share capacity up to one free share and some pickup locations, so the
        #    capacity checks can be exercised by hand.
        # All share the same bidders and calibration, so only one may be active.
        year = next_period.start_date.year
        traffic_light_round = BiddingRoundService.create_round(
            growing_period=next_period,
            name=f"Beitragsrunde {year} - Ampel",
            bidding_procedure=TRAFFIC_LIGHT,
            end_at=end_at,
            start_at=now,
            product_type_id=harvest_share_product_type.id,
            cache=cache,
        )
        simple_round = BiddingRoundService.create_round(
            growing_period=next_period,
            name=f"Beitragsrunde {year} - einfach",
            bidding_procedure=SIMPLE,
            end_at=end_at,
            start_at=now,
            product_type_id=harvest_share_product_type.id,
            bid_levels=1,
            cache=cache,
        )
        simple_levels_round = BiddingRoundService.create_round(
            growing_period=next_period,
            name=f"Beitragsrunde {year} - einfach - 3 Gebote",
            bidding_procedure=SIMPLE,
            end_at=end_at,
            start_at=now,
            product_type_id=harvest_share_product_type.id,
            bid_levels=3,
            cache=cache,
        )
        capacity_round = BiddingRoundService.create_round(
            growing_period=next_period,
            name=f"Beitragsrunde {year} - Kapazitätstest",
            bidding_procedure=SIMPLE,
            end_at=end_at,
            start_at=now,
            product_type_id=harvest_share_product_type.id,
            bid_levels=1,
            cache=cache,
        )

        products = list(
            Product.objects.filter(type=harvest_share_product_type, deleted=False)
        )
        # The reference value and the minimum amount are stored per share size (1:1,
        # no scaling in the app). The demo values are proportional to the size so that
        # switching the share scales the bid, as in the previous implementation.
        size_by_product_id = {}
        for product in products:
            product_price = get_product_price(
                product=product,
                reference_date=next_period.start_date,
                cache=cache,
            )
            size_by_product_id[product.id] = (
                Decimal(product_price.size)
                if product_price is not None and product_price.size
                else Decimal("1")
            )
        for bidding_round in (
            traffic_light_round,
            simple_round,
            simple_levels_round,
            capacity_round,
        ):
            round_product = bidding_round.products.get()
            round_product.target_amount_per_year = TARGET_AMOUNT_PER_YEAR
            round_product.save(update_fields=["target_amount_per_year"])
            for product in products:
                size = size_by_product_id[product.id]
                BiddingRoundProductPrice.objects.update_or_create(
                    round_product=round_product,
                    product=product,
                    defaults={
                        "reference_value": (REFERENCE_VALUE * size).quantize(
                            Decimal("0.01")
                        ),
                        "min_amount": (MIN_AMOUNT * size).quantize(Decimal("0.01")),
                    },
                )

        active_subscriptions = get_active_subscriptions(cache=cache).filter(
            product__type=harvest_share_product_type
        )
        existing_members = sorted(
            {subscription.member for subscription in active_subscriptions},
            key=lambda member: member.id,
        )

        number_of_existing_members = len(existing_members)
        number_of_bidders = int(math.floor(number_of_existing_members * 0.6))

        bidders = existing_members[:number_of_bidders]

        # Shares that will renew per member (in harvest shares), used to keep the
        # auto-renewal contribution at about 20 % of the season capacity.
        renewal_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=next_period.start_date, cache={}
            )
        )
        shares_by_member_id = {}
        for subscription in renewal_subscriptions:
            if subscription.product.type_id != harvest_share_product_type.id:
                continue
            product_price = get_product_price(
                product=subscription.product,
                reference_date=next_period.start_date,
                cache=cache,
            )
            size = (
                Decimal(product_price.size)
                if product_price is not None and product_price.size
                else Decimal("1")
            )
            shares_by_member_id[subscription.member_id] = (
                shares_by_member_id.get(subscription.member_id, Decimal("0"))
                + size * subscription.quantity
            )

        auto_renew_share_budget = capacities[0].capacity * AUTO_RENEW_SHARES_RATIO
        auto_renew_shares = Decimal("0")
        auto_renew_members = []
        cancelled_members = []
        for member in existing_members[number_of_bidders:]:
            member_shares = shares_by_member_id.get(member.id, Decimal("0"))
            if (
                not auto_renew_members
                or auto_renew_shares + member_shares <= auto_renew_share_budget
            ):
                auto_renew_members.append(member)
                auto_renew_shares += member_shares
            else:
                cancelled_members.append(member)

        now = get_now(cache=cache)
        for member in cancelled_members:
            Subscription.objects.filter(
                member=member, cancellation_ts__isnull=True
            ).update(cancellation_ts=now)

        number_of_new_members = int(round(number_of_existing_members * 0.1))
        new_members = [MemberFactory.create() for _ in range(number_of_new_members)]
        bidders = bidders + new_members

        pickup_locations = list(PickupLocation.objects.all())
        product_type_ids = [capacity.product_type_id for capacity in capacities]
        capacity_by_product_type_id = {
            capacity.product_type_id: capacity for capacity in capacities
        }

        # Products of each biddable product type, ordered by size.
        products_by_product_type_id = {}
        for product_type_id in product_type_ids:
            products_with_size = []
            for product in Product.objects.filter(
                type_id=product_type_id, deleted=False
            ):
                product_price = get_product_price(
                    product=product,
                    reference_date=next_period.start_date,
                    cache=cache,
                )
                size = (
                    Decimal(product_price.size)
                    if product_price is not None and product_price.size
                    else Decimal("1")
                )
                products_with_size.append((product, size))
            if products_with_size:
                products_by_product_type_id[product_type_id] = sorted(
                    products_with_size, key=lambda entry: entry[1]
                )

        bidders_by_product_type_id = {
            product_type_id: [] for product_type_id in product_type_ids
        }
        for idx, member in enumerate(bidders):
            product_type_id = product_type_ids[idx % len(product_type_ids)]
            if product_type_id in products_by_product_type_id:
                bidders_by_product_type_id[product_type_id].append(member)

        # Contributions that do not depend on the traffic_light level: auto-renewed
        # members (reference value) and delivery charges of the chosen depots.
        # A fresh cache is used so that the just-set cancellations are visible.
        bidder_member_ids = {member.id for member in bidders}
        auto_renew_euro_by_product_type_id = {}
        auto_renew_shares_by_product_type_id = {}
        auto_renew_shares_by_location_id = {}
        auto_renewed_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=next_period.start_date, cache={}
            )
        )
        for subscription in auto_renewed_subscriptions:
            if subscription.member_id in bidder_member_ids:
                continue
            product_type_id = subscription.product.type_id
            if product_type_id not in products_by_product_type_id:
                continue
            subscription_price = get_product_price(
                product=subscription.product,
                reference_date=next_period.start_date,
                cache=cache,
            )
            size = (
                Decimal(subscription_price.size)
                if subscription_price is not None and subscription_price.size
                else Decimal("1")
            )
            auto_renew_euro_by_product_type_id[product_type_id] = (
                auto_renew_euro_by_product_type_id.get(product_type_id, Decimal("0"))
                + REFERENCE_VALUE * size * subscription.quantity * 12
            )
            auto_renew_shares_by_product_type_id[product_type_id] = (
                auto_renew_shares_by_product_type_id.get(product_type_id, Decimal("0"))
                + size * subscription.quantity
            )
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=subscription.member_id,
                    reference_date=next_period.start_date,
                    cache=cache,
                )
            )
            if pickup_location_id:
                auto_renew_shares_by_location_id[pickup_location_id] = (
                    auto_renew_shares_by_location_id.get(
                        pickup_location_id, Decimal("0")
                    )
                    + size * subscription.quantity
                )

        # Assign each bidder a variant and a small random factor. The variants are
        # chosen so that the bids plus the auto-renewed shares fill about 90 % of
        # the season capacity, and the factor gives the individual bids variance.
        bidder_assignments = []
        for product_type_id, type_bidders in bidders_by_product_type_id.items():
            products_with_size = products_by_product_type_id[product_type_id]
            target_bid_shares = max(
                capacity_by_product_type_id[product_type_id].capacity
                * SHARES_TARGET_RATIO
                - auto_renew_shares_by_product_type_id.get(
                    product_type_id, Decimal("0")
                ),
                Decimal("0"),
            )
            chosen_sizes = _choose_sizes(
                [size for _, size in products_with_size],
                len(type_bidders),
                target_bid_shares,
            )
            product_by_size = {size: product for product, size in products_with_size}
            for member, size in zip(type_bidders, chosen_sizes):
                factor = Decimal(str(round(random.uniform(0.85, 1.15), 3)))
                bidder_assignments.append(
                    (member, product_type_id, product_by_size[size], size, factor)
                )

        primary_location_by_index = cls._assign_bidder_pickup_locations(
            bidder_assignments=bidder_assignments,
            pickup_locations=pickup_locations,
            organization=organization,
        )

        delivery_charge_by_product_type_id = {}
        if pickup_locations:
            for index, assignment in enumerate(bidder_assignments):
                product_type_id = assignment[1]
                pickup_location = primary_location_by_index.get(index)
                if pickup_location is None:
                    continue
                delivery_charge = (
                    BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
                        pickup_location_id=pickup_location.id,
                        product_type=products_by_product_type_id[product_type_id][0][
                            0
                        ].type,
                        growing_period=next_period,
                        cache=cache,
                    )
                )
                delivery_charge_by_product_type_id[product_type_id] = (
                    delivery_charge_by_product_type_id.get(
                        product_type_id, Decimal("0")
                    )
                    + delivery_charge
                )

        # Calibrate the per-share amounts so that the total (bids + auto-renewal +
        # delivery) is 81/91/109 % of the season target for green/yellow/red. The
        # random factors are accounted for, so the totals stay on target.
        weighted_shares_by_product_type_id = {}
        for _, product_type_id, _, size, factor in bidder_assignments:
            weighted_shares_by_product_type_id[product_type_id] = (
                weighted_shares_by_product_type_id.get(product_type_id, Decimal("0"))
                + size * factor
            )

        green_per_share_by_product_type_id = {}
        yellow_per_share_by_product_type_id = {}
        red_per_share_by_product_type_id = {}
        for (
            product_type_id,
            weighted_shares,
        ) in weighted_shares_by_product_type_id.items():
            if weighted_shares == 0:
                continue
            fixed = auto_renew_euro_by_product_type_id.get(
                product_type_id, Decimal("0")
            ) + delivery_charge_by_product_type_id.get(product_type_id, Decimal("0"))
            divisor = weighted_shares * 12
            green_per_share_by_product_type_id[product_type_id] = (
                TARGET_AMOUNT_PER_YEAR * GREEN_TARGET_RATIO - fixed
            ) / divisor
            yellow_per_share_by_product_type_id[product_type_id] = (
                TARGET_AMOUNT_PER_YEAR * YELLOW_TARGET_RATIO - fixed
            ) / divisor
            red_per_share_by_product_type_id[product_type_id] = (
                TARGET_AMOUNT_PER_YEAR * RED_TARGET_RATIO - fixed
            ) / divisor

        # Amounts and depots are computed once and used for all rounds, so the
        # simple rounds reuse exactly the calibrated level amounts (green for the
        # level-1 and level-3 simple round, yellow for the single-bid round).
        bid_rows = []
        for idx, (member, product_type_id, product, size, factor) in enumerate(
            bidder_assignments
        ):
            bid_rows.append(
                {
                    "member": member,
                    "product_type_id": product_type_id,
                    "product": product,
                    "green": (
                        green_per_share_by_product_type_id[product_type_id]
                        * size
                        * factor
                    ).quantize(Decimal("0.01")),
                    "yellow": (
                        yellow_per_share_by_product_type_id[product_type_id]
                        * size
                        * factor
                    ).quantize(Decimal("0.01")),
                    "red": (
                        red_per_share_by_product_type_id[product_type_id]
                        * size
                        * factor
                    ).quantize(Decimal("0.01")),
                    "pickup_location": primary_location_by_index.get(idx),
                }
            )

        cls._create_bids(
            traffic_light_round, bid_rows, level_keys=["green", "yellow", "red"]
        )
        cls._create_bids(simple_round, bid_rows, level_keys=["yellow"])
        cls._create_bids(
            simple_levels_round, bid_rows, level_keys=["green", "yellow", "red"]
        )

        # The capacity test round reuses the same base bids plus additional bids of
        # new members, so that the harvest share capacity is filled up to one free
        # share and some pickup locations are full. The auto-renewals are unchanged.
        extra_bid_rows = cls._build_capacity_test_bid_rows(
            capacities=capacities,
            products_by_product_type_id=products_by_product_type_id,
            bidder_assignments=bidder_assignments,
            primary_location_by_index=primary_location_by_index,
            auto_renew_shares_by_location_id=auto_renew_shares_by_location_id,
            auto_renew_shares_by_product_type_id=auto_renew_shares_by_product_type_id,
            yellow_per_share_by_product_type_id=yellow_per_share_by_product_type_id,
            pickup_locations=pickup_locations,
            organization=organization,
        )
        cls._create_bids(capacity_round, bid_rows, level_keys=["yellow"])
        cls._create_bids(capacity_round, extra_bid_rows, level_keys=["yellow"])
        cls._ensure_one_free_share_in_capacity_test_round(
            capacity_round=capacity_round,
            extra_bid_rows=extra_bid_rows,
        )

        # The traffic_light round and the three-level simple round are kept as evaluated
        # (closed) rounds. The capacity test round is the active public round so that
        # the capacity checks can be tested by hand; only one round may be active.
        BiddingRoundService.start_round(traffic_light_round, cache=cache)
        BiddingRoundService.close_round(traffic_light_round, cache=cache)
        BiddingRoundService.start_round(simple_levels_round, cache=cache)
        BiddingRoundService.close_round(simple_levels_round, cache=cache)
        BiddingRoundService.start_round(simple_round, cache=cache)
        BiddingRoundService.close_round(simple_round, cache=cache)
        BiddingRoundService.start_round(capacity_round, cache=cache)

        return capacity_round

    @classmethod
    def _build_capacity_test_bid_rows(
        cls,
        capacities,
        products_by_product_type_id,
        bidder_assignments,
        primary_location_by_index,
        auto_renew_shares_by_location_id,
        auto_renew_shares_by_product_type_id,
        yellow_per_share_by_product_type_id,
        pickup_locations,
        organization,
    ):
        """
        Build extra bids (of extra new members) for the capacity test round so that the
        total occupied capacity (base bids + auto-renewals + extra bids) reaches the
        harvest share capacity minus one share, and the smallest pickup locations fill
        up first. Returns an empty list if there is no room left.
        """
        if not capacities or not pickup_locations:
            return []

        product_type_id = capacities[0].product_type_id
        capacity = Decimal(capacities[0].capacity or 0)
        products_with_size = products_by_product_type_id.get(product_type_id)
        if not products_with_size:
            return []
        smallest_product, smallest_size = products_with_size[0]

        base_bid_units = sum(
            (size for _, _, _, size, _ in bidder_assignments), Decimal("0")
        )
        auto_renew_units = auto_renew_shares_by_product_type_id.get(
            product_type_id, Decimal("0")
        )
        extra_units = capacity - 1 - base_bid_units - auto_renew_units

        extra_sizes = []
        remaining = extra_units
        while remaining >= smallest_size:
            extra_sizes.append(smallest_size)
            remaining -= smallest_size
        if not extra_sizes:
            return []

        base_demand_by_location_id = {}
        for index, (_, _, _, size, _) in enumerate(bidder_assignments):
            location = primary_location_by_index.get(index)
            if location is None:
                continue
            base_demand_by_location_id[location.id] = (
                base_demand_by_location_id.get(location.id, Decimal("0")) + size
            )

        capacity_by_location_id = {}
        for capability in PickupLocationCapability.objects.filter(
            product_type_id=product_type_id
        ):
            capacity_by_location_id[capability.pickup_location_id] = (
                capacity_by_location_id.get(capability.pickup_location_id, Decimal("0"))
                + Decimal(capability.max_capacity or 0)
            )

        primary_by_index = cls._assign_capacity_test_locations(
            extra_sizes=extra_sizes,
            capacity_by_location_id=capacity_by_location_id,
            base_demand_by_location_id=base_demand_by_location_id,
            auto_renew_shares_by_location_id=auto_renew_shares_by_location_id,
            pickup_locations=pickup_locations,
        )

        extra_members = [MemberFactory.create() for _ in extra_sizes]

        yellow_per_share = yellow_per_share_by_product_type_id.get(
            product_type_id, Decimal("0")
        )
        extra_bid_rows = []
        for index, member in enumerate(extra_members):
            extra_bid_rows.append(
                {
                    "member": member,
                    "product_type_id": product_type_id,
                    "product": smallest_product,
                    "yellow": (yellow_per_share * smallest_size).quantize(
                        Decimal("0.01")
                    ),
                    "pickup_location": primary_by_index.get(index),
                }
            )
        return extra_bid_rows

    @classmethod
    def _ensure_one_free_share_in_capacity_test_round(
        cls, capacity_round, extra_bid_rows
    ):
        """
        The projected occupancy can differ slightly from the predicted one because the
        capacity checkers compute renewals with their own reference date. Remove extra
        bids until a one-share bid is accepted again, so that exactly one share stays
        free (we target capacity - 1). A fresh cache per probe is used so that removed
        bids are visible to the check.
        """
        if not extra_bid_rows:
            return
        probing_items = [{"product_id": extra_bid_rows[0]["product"].id, "quantity": 1}]
        while extra_bid_rows:
            reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
                bidding_round=capacity_round,
                items=probing_items,
                pickup_location_id=None,
                member=None,
                cache={},
            )
            if not reasons:
                return
            removed = extra_bid_rows.pop()
            Bid.objects.filter(round=capacity_round, member=removed["member"]).delete()

    @classmethod
    def _assign_capacity_test_locations(
        cls,
        extra_sizes,
        capacity_by_location_id,
        base_demand_by_location_id,
        auto_renew_shares_by_location_id,
        pickup_locations,
    ):
        """
        Assign the extra bids greedily to the pickup locations with the least free
        capacity first, so that the smallest locations fill up and at least one of them
        is at capacity. Returns ``{index: pickup_location}``.
        """
        free_by_location_id = {}
        for location in pickup_locations:
            free_by_location_id[location.id] = (
                capacity_by_location_id.get(location.id, Decimal("0"))
                - base_demand_by_location_id.get(location.id, Decimal("0"))
                - auto_renew_shares_by_location_id.get(location.id, Decimal("0"))
            )

        primary = {}
        for index, size in enumerate(extra_sizes):
            candidates = sorted(
                pickup_locations,
                key=lambda location: (free_by_location_id[location.id], location.name),
            )
            chosen = candidates[0]
            for candidate in candidates:
                if free_by_location_id[candidate.id] >= size:
                    chosen = candidate
                    break
            free_by_location_id[chosen.id] -= size
            primary[index] = chosen
        return primary

    @classmethod
    def _assign_bidder_pickup_locations(
        cls, bidder_assignments, pickup_locations, organization
    ):
        """
        Assign a primary pickup location to every bidder.

        For Vierlande the bids are distributed over the city/land depot groups so that
        about 62 % of the bid share units land in the city depots and about 38 % in the
        land depots, proportionally to the depot capacities within each group. Every
        other organization keeps the previous round-robin assignment.
        """
        number_of_bidders = len(bidder_assignments)
        if not pickup_locations or number_of_bidders == 0:
            return {}

        if organization == Organization.VIERLANDE:
            vierlande_assignment = VierlandeGenerator.assign_bidder_pickup_locations(
                bidder_assignments=bidder_assignments,
                pickup_locations=pickup_locations,
            )
            if vierlande_assignment is not None:
                return vierlande_assignment

        return {
            index: pickup_locations[index % len(pickup_locations)]
            for index in range(number_of_bidders)
        }

    @staticmethod
    def _create_bids(bidding_round, bid_rows, level_keys):
        for row in bid_rows:
            round_product = BiddingRoundProduct.objects.get(
                round=bidding_round, product_type_id=row["product_type_id"]
            )
            bid = Bid.objects.create(
                round=bidding_round,
                member=row["member"],
                pickup_location=row["pickup_location"],
            )
            amounts = [row[key] for key in level_keys]
            BidItem.objects.create(
                bid=bid,
                round_product=round_product,
                product=row["product"],
                quantity=1,
                amount_1=amounts[0] if len(amounts) > 0 else None,
                amount_2=amounts[1] if len(amounts) > 1 else None,
                amount_3=amounts[2] if len(amounts) > 2 else None,
            )
