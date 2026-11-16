from decimal import Decimal

from tapir.bidding_round.config import BIDDING_ROUND_STATUS_CLOSED
from tapir.bidding_round.models import BiddingRound
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, Subscription


from tapir.bidding_round.services.bidding_round_previous_amount_service import (
    BiddingRoundPreviousAmountService,
)


class NonBidderContributionService:
    """
    Global rule: non-bidders pay at least the bidders' average bid.
    Applied to auto-renewed members when the round is closed and to latecomers when
    they join, depending on the round's contribution mode. Existing higher
    contributions/overrides are never lowered.
    """

    @classmethod
    def _get_size(cls, subscription, bidding_round, cache) -> Decimal:
        return BiddingRoundStatsService.get_product_size(
            subscription.product, bidding_round, cache
        )

    @classmethod
    def _get_product_type_ids(cls, bidding_round) -> set[str]:
        return {bidding_round.product_type_id}

    @classmethod
    def _get_bid_member_ids(cls, bidding_round) -> set[str]:
        return set(bidding_round.bids.values_list("member_id", flat=True))

    @classmethod
    def _filter_non_bidder_subscriptions(
        cls,
        subscriptions,
        product_type_ids,
        bid_member_ids,
        member_id=None,
    ) -> list[Subscription]:
        """Keep the round's subscriptions whose member did not bid and whose
        product belongs to one of the round's product types. Optionally
        restricted to a single member."""
        return [
            subscription
            for subscription in subscriptions
            if subscription.product.type_id in product_type_ids
            and subscription.member_id not in bid_member_ids
            and (member_id is None or subscription.member_id == member_id)
        ]

    @classmethod
    def apply_non_bidder_contributions(
        cls, bidding_round, actor, cache, exclude_member_ids=None
    ) -> list[str]:
        from tapir.bidding_round.services.contract_creator import ContractCreator

        product_type_ids = cls._get_product_type_ids(bidding_round)
        bid_member_ids = cls._get_bid_member_ids(bidding_round)
        period = bidding_round.growing_period

        renewing_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=period.start_date, cache=cache
            )
        )
        member_ids = {
            subscription.member_id
            for subscription in cls._filter_non_bidder_subscriptions(
                renewing_subscriptions, product_type_ids, bid_member_ids
            )
        }
        member_ids.update(
            subscription.member_id
            for subscription in cls._filter_non_bidder_subscriptions(
                Subscription.objects.filter(
                    period=period,
                    product__type_id__in=product_type_ids,
                    cancellation_ts__isnull=True,
                ).select_related("product"),
                product_type_ids,
                bid_member_ids,
            )
        )
        member_ids -= {str(member_id) for member_id in (exclude_member_ids or [])}

        members = Member.objects.in_bulk(list(member_ids))
        applied = []
        for member_id, member in members.items():
            if ContractCreator.apply_non_bidder_floor(
                bidding_round, member, actor, cache
            ):
                applied.append(member_id)
        return applied

    @classmethod
    def apply_floor_to_member(
        cls,
        member,
        bidding_round,
        actor,
        cache,
        rate=None,
        contribution_start_date=None,
        product_type_ids=None,
        bid_member_ids=None,
    ) -> SolidarityContribution | None:
        if rate is None:
            rate = cls._get_rate(bidding_round, cache)

        if product_type_ids is None:
            product_type_ids = cls._get_product_type_ids(bidding_round)
        if bid_member_ids is None:
            bid_member_ids = cls._get_bid_member_ids(bidding_round)

        if member.id in bid_member_ids:
            return None

        period = bidding_round.growing_period
        reference_date = contribution_start_date or period.start_date

        next_period_subscriptions = cls._filter_non_bidder_subscriptions(
            Subscription.objects.filter(
                member=member,
                period=period,
                product__type_id__in=product_type_ids,
                cancellation_ts__isnull=True,
            ).select_related("product"),
            product_type_ids,
            bid_member_ids,
        )
        basis_subscriptions = next_period_subscriptions or cls._filter_non_bidder_subscriptions(
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=reference_date, cache=cache
            ),
            product_type_ids,
            bid_member_ids,
            member_id=member.id,
        )
        if not basis_subscriptions:
            return None

        free_auto_renewed = [
            subscription
            for subscription in basis_subscriptions
            if subscription.price_override == 0
            and subscription.price_mode
            == Subscription.PriceMode.BIDDING_ROUND_AUTO_RENEWED
        ]
        basis_subscriptions = [
            subscription
            for subscription in basis_subscriptions
            if subscription not in free_auto_renewed
        ]
        if not basis_subscriptions:
            return None

        contract_monthly_total = Decimal("0")
        floor_monthly_total = Decimal("0")
        for subscription in basis_subscriptions:
            size = cls._get_size(subscription, bidding_round, cache)
            contract_monthly_total += SubscriptionPriceCalculator.get_monthly_price(
                subscription, reference_date=reference_date, cache=cache
            )
            floor_monthly_total += size * subscription.quantity * rate

        previous_monthly_total = BiddingRoundPreviousAmountService.get_previous_amount(
            member.id, bidding_round, product_type_ids, cache
        ) or Decimal("0")
        target_monthly_total = max(floor_monthly_total, previous_monthly_total)
        current_contribution = (
            MemberSolidarityContributionService.get_member_contribution(
                member_id=member.id, reference_date=reference_date, cache=cache
            )
            or Decimal("0")
        )
        if contract_monthly_total + current_contribution >= target_monthly_total:
            return None

        return MemberSolidarityContributionService.assign_contribution_to_member(
            member=member,
            change_date=reference_date,
            amount=target_monthly_total - contract_monthly_total,
            cache=cache,
            actor=actor,
        )

    @classmethod
    def apply_latecomer_floor(cls, member, contract_start_date, actor, cache):
        """Floor for members joining after/around a closed round (late joiners)."""

        period = TapirCache.get_growing_period_at_date(
            reference_date=contract_start_date, cache=cache
        )
        if period is None:
            return None
        bidding_round = (
            BiddingRound.objects.filter(
                growing_period=period,
                status=BIDDING_ROUND_STATUS_CLOSED,
                contracts_created_at__isnull=False,
            )
            .order_by("-contracts_created_at")
            .first()
        )
        if bidding_round is None:
            return None
        return cls.apply_floor_to_member(
            member=member,
            bidding_round=bidding_round,
            actor=actor,
            cache=cache,
            contribution_start_date=contract_start_date,
        )

    @classmethod
    def _get_rate(cls, bidding_round, cache) -> Decimal:
        cache_key = ("bidding_round_non_bidder_rate", bidding_round.id)
        if cache_key not in cache:
            cache[cache_key] = BiddingRoundStatsService.build_non_bidder_rate_per_share(
                bidding_round, cache=cache
            )
        return cache[cache_key]
