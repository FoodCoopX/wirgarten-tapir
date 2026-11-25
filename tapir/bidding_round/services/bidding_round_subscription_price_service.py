from decimal import Decimal

from django.db.models import F, OuterRef, Q, QuerySet, Subquery, When

from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.wirgarten.models import Subscription


class BiddingRoundSubscriptionPriceService:
    """Prices contracts whose price comes from a bidding round.

    The round result is frozen on ``BiddingRoundCreatedSubscription.monthly_price_per_share``
    when the contract is created, so later changes to the round or to
    ``ProductPrice`` cannot move a price that is already fixed.
    """

    PRICE_MODES = (
        Subscription.PriceMode.BIDDING_ROUND_BID,
        Subscription.PriceMode.BIDDING_ROUND_AUTO_RENEWED,
    )
    ANNOTATION_PRICE_PER_SHARE = "bidding_round_price_per_share"

    @classmethod
    def get_price_for_subscription(
        cls, subscription: Subscription, cache: dict
    ) -> Decimal | None:
        if subscription.price_override is not None:
            return subscription.price_override
        if subscription.price_mode not in cls.PRICE_MODES:
            return None
        link = cls._get_link(subscription, cache)
        if link is None or link.monthly_price_per_share is None:
            return None
        return link.monthly_price_per_share * subscription.quantity

    @classmethod
    def _get_link(
        cls, subscription: Subscription, cache: dict
    ) -> BiddingRoundCreatedSubscription | None:
        cache_key = ("bidding_round_created_subscription_link", subscription.id)
        if cache_key not in cache:
            cache[cache_key] = (
                BiddingRoundCreatedSubscription.objects.filter(
                    subscription=subscription,
                    round__growing_period=subscription.period,
                )
                .order_by("-round__end_at", "-round__created_at")
                .first()
            )
        return cache[cache_key]

    @classmethod
    def annotate_price_per_share(cls, queryset: QuerySet[Subscription]) -> QuerySet:
        return queryset.annotate(
            **{
                cls.ANNOTATION_PRICE_PER_SHARE: Subquery(
                    BiddingRoundCreatedSubscription.objects.filter(
                        subscription_id=OuterRef("pk"),
                        round__growing_period=OuterRef("period_id"),
                    )
                    .order_by("-round__end_at", "-round__created_at")
                    .values("monthly_price_per_share")[:1]
                )
            }
        )

    @classmethod
    def price_per_share_when(cls) -> When:
        """The ``When`` for the calculator's monthly price case.

        The annotation holds the amount per share, so the case uses it times the
        number of shares.
        """
        return When(
            Q(price_mode__in=cls.PRICE_MODES)
            & Q(**{f"{cls.ANNOTATION_PRICE_PER_SHARE}__isnull": False}),
            then=F(cls.ANNOTATION_PRICE_PER_SHARE) * F("quantity"),
        )

    @classmethod
    def attach_monthly_prices(cls, subscriptions, cache: dict) -> None:
        for subscription in subscriptions:
            if subscription.price_mode not in cls.PRICE_MODES:
                continue
            price = cls.get_price_for_subscription(subscription, cache)
            if price is not None:
                subscription.monthly_price = price
