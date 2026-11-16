from django.db import models

from tapir.bidding_round.config import (
    BIDDING_ROUND_MAX_SHARES,
    BIDDING_ROUND_MIN_SHARES,
    BIDDING_ROUND_STATUS_CONFIGURATION,
    OPTIONS_BIDDING_ROUND_STATUS,
)
from tapir.core.models import TapirModel
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    Product,
    ProductType,
    Subscription,
)


class BiddingRound(TapirModel):
    """One bidding round for a growing period.

    Members submit one amount per share and the number of shares they bid for the
    round's single biddable product type. ``contracts_created_at`` marks the round as
    evaluated: from then on the round is read-only.
    """

    growing_period = models.ForeignKey(GrowingPeriod, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20,
        choices=OPTIONS_BIDDING_ROUND_STATUS,
        default=BIDDING_ROUND_STATUS_CONFIGURATION,
    )
    start_at = models.DateTimeField(null=True)
    end_at = models.DateTimeField(null=False)
    contracts_created_at = models.DateTimeField(null=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class BiddingRoundProductType(TapirModel):
    """The one biddable product type of a round."""

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="product_types"
    )
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    target_amount_per_year = models.DecimalField(
        max_digits=12, decimal_places=2, null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round"], name="uniq_bidding_round_product_type"
            )
        ]

    def __str__(self):
        return f"{self.round} - {self.product_type}"


class BiddingRoundProductPrice(TapirModel):
    """Reference value and minimum amount per share, plus the share size.

    ``reference_value`` and ``min_amount`` apply per share. ``size`` is the
    bidding round's product size and scales the contract price; it is not
    ``ProductPrice.size``.
    """

    round_product_type = models.ForeignKey(
        BiddingRoundProductType, on_delete=models.CASCADE, related_name="prices"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    reference_value = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    min_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    size = models.DecimalField(max_digits=8, decimal_places=4, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round_product_type", "product"],
                name="uniq_bidding_round_product_price",
            )
        ]

    def __str__(self):
        return f"{self.round_product_type} - {self.product}"


class Bid(TapirModel):
    """One bid per member and round.

    The pickup location is not stored on the bid: statistics and contract creation
    use the member's location at the growing period's start date
    (``MemberPickupLocationGetter``).
    """

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="bids"
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round", "member"], name="uniq_bidding_round_member"
            )
        ]

    def __str__(self):
        return f"{self.round} - {self.member}"


class BidItem(TapirModel):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name="items")
    round_product_type = models.ForeignKey(
        BiddingRoundProductType, on_delete=models.CASCADE
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1)
    amount_1 = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bid", "round_product_type"],
                name="uniq_bid_item_round_product_type",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=BIDDING_ROUND_MIN_SHARES)
                & models.Q(quantity__lte=BIDDING_ROUND_MAX_SHARES),
                name="bid_item_quantity_between_1_and_5",
            ),
        ]

    def __str__(self):
        return f"{self.bid} - {self.product} ({self.quantity} x {self.amount_1})"


class BiddingRoundCreatedSubscription(TapirModel):
    """Links a subscription created by a bidding round to that round, so the created
    contracts can be listed. A subscription can be linked once per round."""

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="created_subscriptions"
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round", "subscription"],
                name="uniq_bidding_round_created_subscription",
            )
        ]

    def __str__(self):
        return f"{self.round} - {self.subscription}"
