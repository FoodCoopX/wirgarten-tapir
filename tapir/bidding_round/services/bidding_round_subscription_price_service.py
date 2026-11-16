from decimal import Decimal

from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.wirgarten.models import Subscription


class BiddingRoundSubscriptionPriceService:
    @classmethod
    def get_price_for_subscription(cls, subscription, cache) -> Decimal | None:
        if subscription.price_override is not None:
            return subscription.price_override
        if subscription.price_mode not in (
            Subscription.PriceMode.BIDDING_ROUND_BID,
            Subscription.PriceMode.BIDDING_ROUND_AUTO_RENEWED,
        ):
            return None
        link = (
            BiddingRoundCreatedSubscription.objects.filter(
                subscription=subscription,
                round__growing_period=subscription.period,
            )
            .select_related("round")
            .order_by("-round__end_at", "-round__created_at")
            .first()
        )
        if link is None:
            return None
        size = BiddingRoundStatsService.get_product_size(
            subscription.product, link.round, cache
        )
        if subscription.price_mode == Subscription.PriceMode.BIDDING_ROUND_BID:
            rate = BiddingRoundStatsService.get_bidder_average_per_share_per_month(
                link.round, cache
            )
        else:
            return None
        return rate * size * subscription.quantity
