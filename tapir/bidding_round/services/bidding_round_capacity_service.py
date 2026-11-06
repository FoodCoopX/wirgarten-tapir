from decimal import Decimal

from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import (
    PickupLocation,
    Product,
    ProductCapacity,
    ProductType,
)
from tapir.wirgarten.service.products import get_product_price


class BiddingRoundCapacityService:
    """
    Shared capacity check for bids. It is used both when a bid is submitted (for
    existing members and for new members registering through the bidding round) and
    when contracts are created after the round has ended, so that both paths check the
    exact same capacities:
    - the global harvest share capacity of the round's product types and
    - the capacity of the primary pickup location.

    Automatic renewals count as usage (handled by the underlying checkers); the
    bidding member's own projected renewal is credited back so that existing members
    can always replace their own renewal with a bid.

    Bids of other members of the same round are also counted as usage: a member either
    auto-renews (contract) or bids, so the bid of a member replaces their projected
    renewal (counted once, not twice) and a bid without a renewal (e.g. of a new member)
    additionally occupies capacity. Bids whose contracts have already been created are
    not counted again.
    """

    REASON_TYPE_PRODUCT_TYPE = "product_type"
    REASON_TYPE_PICKUP_LOCATION = "pickup_location"

    @classmethod
    def build_insufficient_capacity_message(cls, reasons: list[dict]):
        product_type_names = ", ".join(
            reason["name"]
            for reason in reasons
            if reason["type"] == cls.REASON_TYPE_PRODUCT_TYPE
        )
        pickup_location_names = ", ".join(
            reason["name"]
            for reason in reasons
            if reason["type"] == cls.REASON_TYPE_PICKUP_LOCATION
        )
        if product_type_names and pickup_location_names:
            return _(
                "Nicht genügend Kapazität für die Produkttypen %(product_types)s und für den Abholort %(pickup_locations)s."
            ) % {
                "product_types": product_type_names,
                "pickup_locations": pickup_location_names,
            }
        if product_type_names:
            return _(
                "Nicht genügend Kapazität für die Produkttypen %(product_types)s."
            ) % {"product_types": product_type_names}
        return _("Nicht genügend Kapazität für den Abholort %(pickup_locations)s.") % {
            "pickup_locations": pickup_location_names
        }

    @classmethod
    def get_contract_start_date(cls, bidding_round, cache):
        growing_period = bidding_round.growing_period
        try:
            contract_start_date = ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period,
                apply_buffer_time=True,
                cache=cache,
            )
        except KeyError:
            # Some configuration parameters (e.g. the delivery change limit) may not be
            # importable in a bare context. Fall back to the period start, which the
            # contract creation path uses as well.
            return growing_period.start_date

        if (
            contract_start_date is None
            or contract_start_date < growing_period.start_date
            or contract_start_date > growing_period.end_date
        ):
            # The capacity of a round can only be evaluated within the round's period.
            return growing_period.start_date
        return contract_start_date

    @classmethod
    def _get_renewal_capacity_by_member(cls, reference_date, cache) -> dict:
        """
        Capacity of each member's subscriptions that will be renewed into the round's
        period but are not materialised yet. The capacity checkers count these renewals
        as usage, so they must be credited back as a member's own existing capacity -
        otherwise a bid that only replaces the member's own renewal is rejected as
        "insufficient capacity".
        """
        cache_key = f"bidding_round_renewal_capacity_by_member_{reference_date}"
        if cache_key in cache:
            return cache[cache_key]
        try:
            renewing_subscriptions = AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=reference_date, cache=cache
            )
        except KeyError:
            renewing_subscriptions = set()

        result = {}
        for subscription in renewing_subscriptions:
            by_product_type = result.setdefault(subscription.member_id, {})
            product_type_id = subscription.product.type_id
            by_product_type[product_type_id] = by_product_type.get(
                product_type_id, Decimal("0")
            ) + subscription.get_used_capacity(cache=cache)
        cache[cache_key] = result
        return result

    @classmethod
    def _get_bid_capacity_by_member(cls, bidding_round, reference_date, cache) -> dict:
        """
        Capacity that each member's bids of the round occupy, computed once per
        round/date and cached in the request cache: member_id -> {"by_product_type":
        {...}, "by_pickup_location": {...}}. The underlying checkers only know about
        subscriptions and renewals, so this is added on top of them.
        """
        cache_key = (
            f"bidding_round_bid_capacity_by_member_{bidding_round.id}_{reference_date}"
        )
        if cache_key in cache:
            return cache[cache_key]

        result = {}
        for bid in bidding_round.bids.prefetch_related("items__product").all():
            entry = result.setdefault(
                bid.member_id, {"by_product_type": {}, "by_pickup_location": {}}
            )
            bid_total = Decimal("0")
            for item in bid.items.all():
                product_price = get_product_price(
                    product=item.product,
                    reference_date=reference_date,
                    cache=cache,
                )
                if product_price is None or not product_price.size:
                    continue
                units = Decimal(product_price.size) * item.quantity
                bid_total += units
                entry["by_product_type"][item.product.type_id] = (
                    entry["by_product_type"].get(item.product.type_id, Decimal("0"))
                    + units
                )
            if bid.pickup_location_id:
                entry["by_pickup_location"][bid.pickup_location_id] = (
                    entry["by_pickup_location"].get(
                        bid.pickup_location_id, Decimal("0")
                    )
                    + bid_total
                )
        cache[cache_key] = result
        return result

    @classmethod
    def _get_extra_capacity_used_by_other_bidders(
        cls, bidding_round, subscription_start_date, checking_member_id, cache
    ) -> tuple[dict, dict]:
        """
        Capacity that the other bidders of the round already occupy but that the
        underlying checkers do not know about (they only see subscriptions and
        renewals). Returned as an additive term per product type (global check) and per
        pickup location (pickup location check).

        For every other bidder the bid's capacity is added and their projected renewal
        is subtracted, so that a bid replacing a renewal is counted exactly once. Bids
        whose contracts have already been created (materialised subscriptions) are
        skipped to avoid double counting, and the checking member is skipped because
        their own renewal is credited back separately. Renewals are only subtracted for
        the product types that the bid actually replaces.
        """
        renewal_capacity_by_member = cls._get_renewal_capacity_by_member(
            reference_date=subscription_start_date, cache=cache
        )
        bid_capacity_by_member = cls._get_bid_capacity_by_member(
            bidding_round=bidding_round,
            reference_date=subscription_start_date,
            cache=cache,
        )
        materialized_member_ids = set(
            BiddingRoundCreatedSubscription.objects.filter(
                round=bidding_round
            ).values_list("subscription__member_id", flat=True)
        )

        extra_by_product_type_id = {}
        extra_by_pickup_location_id = {}
        for member_id, bid_capacity in bid_capacity_by_member.items():
            if member_id == checking_member_id or member_id in materialized_member_ids:
                continue

            renewal_capacity_by_product_type_id = renewal_capacity_by_member.get(
                member_id, {}
            )
            by_product_type = bid_capacity["by_product_type"]

            for product_type_id, units in by_product_type.items():
                extra_by_product_type_id[product_type_id] = (
                    extra_by_product_type_id.get(product_type_id, Decimal("0"))
                    + units
                    - renewal_capacity_by_product_type_id.get(
                        product_type_id, Decimal("0")
                    )
                )

            # Only the renewal of the product types that the bid contains is replaced,
            # renewals of other product types (e.g. a bread share) stay as they are.
            replaced_renewal_capacity = sum(
                (
                    renewal_capacity_by_product_type_id.get(
                        product_type_id, Decimal("0")
                    )
                    for product_type_id in by_product_type
                ),
                Decimal("0"),
            )

            for pickup_location_id, units in bid_capacity["by_pickup_location"].items():
                extra_by_pickup_location_id[pickup_location_id] = (
                    extra_by_pickup_location_id.get(pickup_location_id, Decimal("0"))
                    + units
                )

            current_pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=member_id,
                    reference_date=subscription_start_date,
                    cache=cache,
                )
            )
            if current_pickup_location_id:
                extra_by_pickup_location_id[current_pickup_location_id] = (
                    extra_by_pickup_location_id.get(
                        current_pickup_location_id, Decimal("0")
                    )
                    - replaced_renewal_capacity
                )

        return extra_by_product_type_id, extra_by_pickup_location_id

    @classmethod
    def build_order_from_items(cls, items: list[dict]) -> TapirOrder:
        product_ids = [item["product_id"] for item in items]
        products_by_id = Product.objects.in_bulk(product_ids)
        order: TapirOrder = {}
        for item in items:
            product = products_by_id.get(item["product_id"])
            if product is None:
                continue
            order[product] = order.get(product, 0) + item["quantity"]
        return order

    @classmethod
    def get_insufficient_capacity_reasons(
        cls,
        bidding_round,
        items: list[dict],
        pickup_location_id,
        member,
        cache,
        subscription_start_date=None,
    ) -> list[dict]:
        """
        Returns an empty list if there is enough capacity for all ordered items and the
        primary pickup location, otherwise one entry per missing capacity:
        {"type": "product_type"|"pickup_location", "name": str}.
        """
        order = cls.build_order_from_items(items)
        if not order:
            return []

        if subscription_start_date is None:
            subscription_start_date = cls.get_contract_start_date(bidding_round, cache)

        member_id = member.id if member is not None else None

        extra_capacity_used_by_member_by_product_type = {}
        if member_id is not None:
            extra_capacity_used_by_member_by_product_type = (
                cls._get_renewal_capacity_by_member(
                    reference_date=subscription_start_date, cache=cache
                ).get(member_id, {})
            )

        reasons = []

        # Only product types with a configured capacity for the round's period are
        # constrained. Without a ProductCapacity there is no capacity to check (and no
        # product price to compute the used capacity with), so those product types are
        # not blocked.
        product_type_ids_with_capacity = set(
            ProductCapacity.objects.filter(
                period=bidding_round.growing_period
            ).values_list("product_type_id", flat=True)
        )
        order_with_capacity_only = {
            product: quantity
            for product, quantity in order.items()
            if product.type_id in product_type_ids_with_capacity
        }

        # The capacity checkers compute the ordered capacity from the product prices
        # of the period. If a price is missing, the capacity cannot be evaluated, so the
        # check is skipped instead of blocking the bid on a configuration error.
        prices_available = all(
            get_product_price(
                product=product, reference_date=subscription_start_date, cache=cache
            )
            is not None
            for product in order_with_capacity_only
        )

        if order_with_capacity_only:
            (
                extra_capacity_used_by_other_members_by_product_type,
                extra_capacity_used_by_other_members_by_pickup_location_id,
            ) = cls._get_extra_capacity_used_by_other_bidders(
                bidding_round=bidding_round,
                subscription_start_date=subscription_start_date,
                checking_member_id=member_id,
                cache=cache,
            )
        else:
            extra_capacity_used_by_other_members_by_product_type = {}
            extra_capacity_used_by_other_members_by_pickup_location_id = {}

        if prices_available:
            product_type_ids_without_capacity = GlobalCapacityChecker.get_product_type_ids_without_enough_capacity_for_order(
                order_with_all_product_types=order_with_capacity_only,
                member_id=member_id,
                subscription_start_date=subscription_start_date,
                cache=cache,
                check_waiting_list_entries=False,
                extra_capacity_used_by_member_by_product_type=(
                    extra_capacity_used_by_member_by_product_type
                ),
                extra_capacity_used_by_other_members_by_product_type=(
                    extra_capacity_used_by_other_members_by_product_type
                ),
            )
            if product_type_ids_without_capacity:
                for product_type_name in ProductType.objects.filter(
                    id__in=product_type_ids_without_capacity
                ).values_list("name", flat=True):
                    reasons.append(
                        {
                            "type": cls.REASON_TYPE_PRODUCT_TYPE,
                            "name": product_type_name,
                        }
                    )

        from tapir.bidding_round.services.bidding_round_service import (
            BiddingRoundService,
        )

        if (
            prices_available
            and BiddingRoundService.is_pickup_location_change_enabled(cache=cache)
            and pickup_location_id
            and order_with_capacity_only
        ):
            pickup_location = PickupLocation.objects.filter(
                id=pickup_location_id
            ).first()
            if pickup_location is not None:
                pickup_location_extra_by_product_type = {
                    product.type_id: extra_capacity_used_by_other_members_by_pickup_location_id.get(
                        pickup_location_id, Decimal("0")
                    )
                    for product in order_with_capacity_only
                }
                has_capacity = PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                    pickup_location=pickup_location,
                    order=order_with_capacity_only,
                    already_registered_member=member,
                    subscription_start=subscription_start_date,
                    cache=cache,
                    check_waiting_list_entries=False,
                    extra_capacity_used_by_member_by_product_type=(
                        extra_capacity_used_by_member_by_product_type
                    ),
                    extra_capacity_used_by_other_members_by_product_type=(
                        pickup_location_extra_by_product_type
                    ),
                )
                if not has_capacity:
                    reasons.append(
                        {
                            "type": cls.REASON_TYPE_PICKUP_LOCATION,
                            "name": pickup_location.name,
                        }
                    )

        return reasons
