from decimal import Decimal

from tapir.bidding_round.config import CLOSED
from tapir.bidding_round.models import BiddingRound
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.configuration.parameter import get_parameter_value
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
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_product_price


class NonBidderContributionService:
    """
    Country-wide (global) rule: non-bidders pay at least the bidders' average bid.
    Applied to auto-renewed members when the round is closed and to latecomers when
    they join, depending on the round's contribution mode. Existing higher
    contributions/overrides are never lowered.
    """

    @classmethod
    def _get_size(cls, subscription, reference_date, cache) -> Decimal:
        price = get_product_price(
            product=subscription.product,
            reference_date=reference_date,
            cache=cache,
        )
        return Decimal(price.size) if price is not None and price.size else Decimal("1")

    @classmethod
    def apply_non_bidder_contributions(cls, bidding_round, actor, cache) -> list[str]:
        rate = cls._get_rate(bidding_round, cache)
        if rate is None:
            return []

        product_type_ids = set(
            bidding_round.products.values_list("product_type_id", flat=True)
        )
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        period = bidding_round.growing_period

        member_ids = set()
        renewing_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=period.start_date, cache=cache
            )
        )
        for subscription in renewing_subscriptions:
            if (
                subscription.product.type_id in product_type_ids
                and subscription.member_id not in bid_member_ids
            ):
                member_ids.add(subscription.member_id)
        for subscription in Subscription.objects.filter(
            period=period,
            product__type_id__in=product_type_ids,
            cancellation_ts__isnull=True,
        ):
            if subscription.member_id not in bid_member_ids:
                member_ids.add(subscription.member_id)

        members = Member.objects.in_bulk(list(member_ids))
        applied = []
        for member_id, member in members.items():
            if cls.apply_floor_to_member(
                member=member,
                bidding_round=bidding_round,
                actor=actor,
                cache=cache,
            ):
                applied.append(member_id)
        return applied

    @classmethod
    def apply_floor_to_member(cls, member, bidding_round, actor, cache) -> bool:
        rate = cls._get_rate(bidding_round, cache)
        if rate is None:
            return False

        if bidding_round.bids.filter(member=member).exists():
            return False

        product_type_ids = set(
            bidding_round.products.values_list("product_type_id", flat=True)
        )
        period = bidding_round.growing_period
        reference_date = period.start_date

        next_period_subscriptions = list(
            Subscription.objects.filter(
                member=member,
                period=period,
                product__type_id__in=product_type_ids,
                cancellation_ts__isnull=True,
            ).select_related("product")
        )
        basis_subscriptions = next_period_subscriptions or list(
            subscription
            for subscription in AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=reference_date, cache=cache
            )
            if subscription.member_id == member.id
            and subscription.product.type_id in product_type_ids
        )
        if not basis_subscriptions:
            return False

        shares = Decimal("0")
        standard_monthly_total = Decimal("0")
        for subscription in basis_subscriptions:
            shares += cls._get_size(subscription, reference_date, cache) * (
                subscription.quantity
            )
            standard_monthly_total += SubscriptionPriceCalculator.get_monthly_price(
                subscription, reference_date=reference_date, cache=cache
            )
        if shares <= 0:
            return False

        target_monthly_total = rate * shares
        current_contribution = (
            MemberSolidarityContributionService.get_member_contribution(
                member_id=member.id, reference_date=reference_date, cache=cache
            )
            or Decimal("0")
        )
        if standard_monthly_total + current_contribution >= target_monthly_total:
            return False

        MemberSolidarityContributionService.assign_contribution_to_member(
            member=member,
            change_date=reference_date,
            amount=target_monthly_total - standard_monthly_total,
            cache=cache,
            actor=actor,
        )
        return True

    @classmethod
    def apply_latecomer_floor(cls, member, contract_start_date, actor, cache) -> bool:
        """Floor for members joining after/around a closed round (late joiners)."""
        if not get_parameter_value(
            ParameterKeys.BIDDING_ROUND_NON_BIDDERS_MIN_AVERAGE, cache=cache
        ):
            return False

        period = TapirCache.get_growing_period_at_date(
            reference_date=contract_start_date, cache=cache
        )
        if period is None:
            return False
        closed_rounds = list(
            BiddingRound.objects.filter(growing_period=period, status=CLOSED)
        )
        if len(closed_rounds) != 1:
            # No closed round, or several (ambiguous) for this period.
            return False
        bidding_round = closed_rounds[0]
        return cls.apply_floor_to_member(
            member=member,
            bidding_round=bidding_round,
            actor=actor,
            cache=cache,
        )

    @classmethod
    def _get_rate(cls, bidding_round, cache) -> Decimal | None:
        if not get_parameter_value(
            ParameterKeys.BIDDING_ROUND_NON_BIDDERS_MIN_AVERAGE, cache=cache
        ):
            return None
        return BiddingRoundStatsService.build_non_bidder_rate_per_share(
            bidding_round, cache=cache
        )
