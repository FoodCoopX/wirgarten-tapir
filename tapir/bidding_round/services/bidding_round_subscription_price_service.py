from decimal import Decimal

from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.wirgarten.models import Subscription


class BiddingRoundSubscriptionPriceService:
    PRICE_MODES = (
        Subscription.PriceMode.BIDDING_ROUND_BID,
        Subscription.PriceMode.BIDDING_ROUND_AUTO_RENEWED,
    )

    @classmethod
    def get_price_for_subscription(cls, subscription, cache) -> Decimal | None:
        if subscription.price_override is not None:
            return subscription.price_override
        if subscription.price_mode not in cls.PRICE_MODES:
            return None
        link_cache_key = ("bidding_round_created_subscription_link", subscription.id)
        if link_cache_key in cache:
            link = cache[link_cache_key]
        else:
            link = (
                BiddingRoundCreatedSubscription.objects.filter(
                    subscription=subscription,
                    round__growing_period=subscription.period,
                )
                .select_related("round")
                .order_by("-round__end_at", "-round__created_at")
                .first()
            )
            cache[link_cache_key] = link
        if link is None:
            return None
        size = BiddingRoundStatsService.get_product_size(
            subscription.product, link.round, cache
        )
        if subscription.price_mode == Subscription.PriceMode.BIDDING_ROUND_BID:
            rate = BiddingRoundStatsService.get_bidder_average_per_share_per_month(
                link.round, cache=cache
            )
        else:
            reference_value = BiddingRoundStatsService.get_reference_value(
                link.round, subscription.product, cache
            )
            rate = max(
                reference_value,
                BiddingRoundStatsService.build_non_bidder_rate_per_share(
                    link.round, cache
                ),
            )
        return rate * size * subscription.quantity

    @classmethod
    def attach_monthly_prices(cls, subscriptions, cache: dict) -> None:
        for subscription in subscriptions:
            if subscription.price_mode not in cls.PRICE_MODES:
                continue
            price = cls.get_price_for_subscription(subscription, cache)
            if price is not None:
                subscription.monthly_price = price
