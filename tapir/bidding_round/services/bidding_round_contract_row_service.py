from decimal import Decimal

from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.services.bidding_round_previous_amount_service import (
    BiddingRoundPreviousAmountService,
)
from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Subscription


class BiddingRoundContractRowService:
    @classmethod
    def serialize_contracts(
        cls, bidding_round, cache, position=None, bids_by_member_id=None
    ) -> list:
        """Rows of the contracts that exist for the round's season: contracts created
        by the round and already materialised auto-renewed contracts."""
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        if position is None:
            position = BiddingRoundStatsService.get_default_position(
                bidding_round, cache=cache
            )
        rows = {}
        cls._add_bidder_contract_rows(
            rows,
            bidding_round,
            cache,
            position,
            bids_by_member_id=bids_by_member_id,
        )
        cls._add_auto_renewed_contract_rows(rows, bidding_round, cache)
        effect_states = dict(
            bidding_round.member_effects.values_list("member_id", "state")
        )
        for member_id, row in rows.items():
            row["rollback_state"] = effect_states.get(member_id, "none")
        ordered = sorted(
            rows.values(), key=lambda row: (row["member_name"] or "").lower()
        )
        return cls._finalize_contract_rows(ordered)

    @classmethod
    def _get_bid_amounts(cls, bid) -> list[str]:
        item = bid.items.first()
        if item is None:
            return []
        return [
            str(amount)
            for amount in (item.amount_1, item.amount_2, item.amount_3)
            if amount is not None
        ]

    @classmethod
    def _add_bidder_contract_rows(
        cls, rows, bidding_round, cache, position, bids_by_member_id=None
    ) -> None:
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        reference_date = bidding_round.growing_period.start_date
        if bids_by_member_id is None:
            bids_by_member_id = {
                bid.member_id: bid
                for bid in bidding_round.bids.prefetch_related("items").all()
            }
        for link in (
            bidding_round.created_subscriptions.filter(is_bidder_contract=True)
            .select_related(
                "subscription__member",
                "subscription__product",
                "subscription__product__type",
            )
            .all()
        ):
            subscription = link.subscription
            cache[("bidding_round_created_subscription_link", subscription.id)] = link
            bid = bids_by_member_id.get(subscription.member_id)
            row = rows.setdefault(
                subscription.member_id,
                cls._new_contract_row(
                    member=subscription.member,
                    type_="bid",
                    pickup_location_name=cls._get_member_pickup_location_name(
                        subscription.member_id, reference_date, cache
                    ),
                    is_created=True,
                ),
            )
            row["items"].append(cls._build_contract_item(subscription))
            row[
                "standard_amount_per_month"
            ] += SubscriptionPriceCalculator.get_monthly_price(
                subscription, reference_date=reference_date, cache=cache
            )
            if bid is not None:
                row["bid_amounts"] = cls._get_bid_amounts(bid)
                item = next(
                    (
                        bid_item
                        for bid_item in bid.items.all()
                        if bid_item.product_id == subscription.product_id
                    ),
                    None,
                )
                if item is not None:
                    effective_amount = BiddingRoundStatsService.get_effective_amount(
                        item, position, bidding_round
                    )
                    row["bid_effective_amount"] = effective_amount
                    row["amount_per_month"] += effective_amount * subscription.quantity
                    continue
            row["amount_per_month"] += SubscriptionPriceCalculator.get_monthly_price(
                subscription, reference_date=reference_date, cache=cache
            )

    @classmethod
    def _add_auto_renewed_contract_rows(cls, rows, bidding_round, cache) -> None:
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        reference_date = bidding_round.growing_period.start_date
        product_type_ids = set(
            bidding_round.product_types.values_list("product_type_id", flat=True)
        )
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        linked_subscription_ids = set(
            bidding_round.created_subscriptions.values_list(
                "subscription_id", flat=True
            )
        )
        rate = BiddingRoundStatsService.build_non_bidder_rate_per_share(
            bidding_round, cache
        )
        subscriptions = list(
            Subscription.objects.filter(
                period=bidding_round.growing_period,
                cancellation_ts__isnull=True,
                product__type_id__in=product_type_ids,
            )
            .exclude(member_id__in=bid_member_ids)
            .select_related("member", "product", "product__type")
        )
        for link in BiddingRoundCreatedSubscription.objects.filter(
            subscription_id__in=[subscription.id for subscription in subscriptions]
        ).select_related("round"):
            cache[("bidding_round_created_subscription_link", link.subscription_id)] = (
                link
            )
        for subscription in subscriptions:
            size = BiddingRoundStatsService.get_product_size(
                subscription.product, bidding_round, cache
            )
            is_free = (
                subscription.price_override == 0
                and subscription.price_mode
                == Subscription.PriceMode.BIDDING_ROUND_AUTO_RENEWED
            )
            try:
                contract_amount = SubscriptionPriceCalculator.get_monthly_price(
                    subscription, reference_date=reference_date, cache=cache
                )
            except TapirImproperlyConfigured:
                contract_amount = Decimal("0")
            floor_amount = (
                Decimal("0") if is_free else rate * size * subscription.quantity
            )
            previous_amount = BiddingRoundPreviousAmountService.get_previous_amount(
                subscription.member_id, bidding_round, product_type_ids, cache
            )
            current_contribution = (
                MemberSolidarityContributionService.get_member_contribution(
                    member_id=subscription.member_id,
                    reference_date=reference_date,
                    cache=cache,
                )
                or Decimal("0")
            )
            is_created = subscription.id in linked_subscription_ids
            if subscription.member_id not in rows:
                rows[subscription.member_id] = cls._new_contract_row(
                    member=subscription.member,
                    type_="auto_renewed",
                    pickup_location_name=cls._get_member_pickup_location_name(
                        subscription.member_id, reference_date, cache
                    ),
                    is_created=is_created,
                )
            row = rows[subscription.member_id]
            row["is_created"] = row["is_created"] or is_created
            row["items"].append(cls._build_contract_item(subscription))
            row["standard_amount_per_month"] += contract_amount
            row["floor_amount_per_month"] += floor_amount
            row["previous_amount_per_month"] = previous_amount
            row["current_contribution_per_month"] = current_contribution
            row["is_free_auto_renewed"] = is_free

    @classmethod
    def _new_contract_row(cls, member, type_, pickup_location_name, is_created) -> dict:
        return {
            "member_id": member.id,
            "member_name": f"{member.first_name} {member.last_name}",
            "member_email": member.email,
            "type": type_,
            "items": [],
            "pickup_location_name": pickup_location_name,
            "standard_amount_per_month": Decimal("0"),
            "amount_per_month": Decimal("0"),
            "is_created": is_created,
            "bid_amounts": [],
            "bid_effective_amount": None,
            "non_bidder_floor_per_month": None,
            "previous_amount_per_month": None,
            "floor_amount_per_month": Decimal("0"),
            "current_contribution_per_month": Decimal("0"),
            "is_free_auto_renewed": False,
            "rollback_state": "none",
        }

    @classmethod
    def _build_contract_item(cls, subscription) -> dict:
        return {
            "product_type_name": subscription.product.type.name,
            "product_name": subscription.product.name,
            "quantity": subscription.quantity,
        }

    @classmethod
    def _get_member_pickup_location_name(cls, member_id, reference_date, cache) -> str:
        pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=member_id, reference_date=reference_date, cache=cache
            )
        )
        if not pickup_location_id:
            return ""
        pickup_location = TapirCache.get_pickup_location_by_id(
            cache=cache, pickup_location_id=pickup_location_id
        )
        return pickup_location.name if pickup_location else ""

    @classmethod
    def _finalize_contract_rows(cls, rows) -> list:
        for row in rows:
            if row["type"] == "auto_renewed":
                target = max(
                    row["standard_amount_per_month"]
                    + row["current_contribution_per_month"],
                    row["floor_amount_per_month"],
                    row["previous_amount_per_month"] or Decimal("0"),
                )
                row["amount_per_month"] = target
                row["contribution_amount_per_month"] = (
                    target - row["standard_amount_per_month"]
                )
                row["non_bidder_floor_per_month"] = (
                    None
                    if row["is_free_auto_renewed"]
                    else row["floor_amount_per_month"]
                )
            else:
                row["contribution_amount_per_month"] = (
                    row["amount_per_month"] - row["standard_amount_per_month"]
                )
                row["non_bidder_floor_per_month"] = None
            row["standard_amount_per_year"] = row["standard_amount_per_month"] * 12
            row["contribution_amount_per_year"] = (
                row["contribution_amount_per_month"] * 12
            )
            row["amount_per_year"] = row["amount_per_month"] * 12
            row.pop("floor_amount_per_month", None)
            row.pop("current_contribution_per_month", None)
            row.pop("is_free_auto_renewed", None)
        return rows
