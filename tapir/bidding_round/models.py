from decimal import Decimal

from django.db import models
from django.utils import timezone

from tapir.bidding_round.config import (
    BIDDING_ROUND_MAX_SHARES,
    BIDDING_ROUND_MIN_SHARES,
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_PROCEDURE_SIMPLE,
    BIDDING_ROUND_STATUS_CONFIGURATION,
    OPTIONS_BIDDING_ROUND_PROCEDURE,
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

    The round carries the single biddable product type and its target amount per
    year. Members submit one bid per product of that type: one amount per share
    (``BIDDING_ROUND_PROCEDURE_SIMPLE``) or a range of two amounts
    (``BIDDING_ROUND_PROCEDURE_BID_RANGE``: green/wish and red/pain threshold).
    ``contracts_created_at`` marks the round as evaluated: from then on the round is
    read-only.
    """

    growing_period = models.ForeignKey(GrowingPeriod, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20,
        choices=OPTIONS_BIDDING_ROUND_STATUS,
        default=BIDDING_ROUND_STATUS_CONFIGURATION,
    )
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    target_amount_per_year = models.DecimalField(
        max_digits=12, decimal_places=2, null=True
    )
    bidding_procedure = models.CharField(
        max_length=20,
        choices=OPTIONS_BIDDING_ROUND_PROCEDURE,
        default=BIDDING_ROUND_PROCEDURE_SIMPLE,
    )
    bid_levels = models.PositiveSmallIntegerField(default=1)
    include_auto_renewed = models.BooleanField(default=True)
    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField()
    contracts_created_at = models.DateTimeField(null=True)
    comment = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(bid_levels__gte=1) & models.Q(bid_levels__lte=3),
                name="bidding_round_bid_levels_between_1_and_3",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE)
                    | models.Q(bid_levels=2)
                ),
                name="bidding_round_bid_range_requires_two_levels",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class BiddingRoundProductPrice(TapirModel):
    """Reference value and minimum amount per share, plus the round's share size.

    ``reference_value`` and ``min_amount`` apply per share. ``size`` is the round's
    size for the product, not ``ProductPrice.size``: it turns the round's average bid
    into an amount per share and back.
    """

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="prices"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    reference_value = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    min_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    size = models.DecimalField(max_digits=8, decimal_places=4, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round", "product"],
                name="uniq_bidding_round_product_price",
            )
        ]

    def __str__(self):
        return f"{self.round} - {self.product}"


class Bid(TapirModel):
    """One bid per member and round: a product, a number of shares and the amounts.

    ``amount_1`` to ``amount_3`` are the monthly amounts per share of the round's
    procedure; the bid range uses ``amount_1`` as green/wish and ``amount_2`` as
    red/pain threshold. The pickup location is not stored on the bid: statistics and
    contract creation use the member's location at the growing period's start date
    (``MemberPickupLocationGetter``).
    """

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="bids"
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1)
    amount_1 = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    amount_2 = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    amount_3 = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round", "member"], name="uniq_bidding_round_member"
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=BIDDING_ROUND_MIN_SHARES)
                & models.Q(quantity__lte=BIDDING_ROUND_MAX_SHARES),
                name="bid_quantity_between_1_and_5",
            ),
        ]

    def __str__(self):
        amount = self.amount_1 or self.amount_2 or self.amount_3 or Decimal("0")
        return (
            f"{self.round} - {self.member} ({self.product}, {self.quantity} x {amount})"
        )


class BiddingRoundCreatedSubscription(TapirModel):
    """Links a subscription created by a bidding round to that round, so the created
    contracts can be listed. A subscription can be linked once per round.

    ``monthly_price_per_share`` freezes the price the round gave the contract, so later
    changes to the round's results or to ``ProductPrice`` cannot move it.
    """

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="created_subscriptions"
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="+"
    )
    monthly_price_per_share = models.DecimalField(
        max_digits=8, decimal_places=4, null=True
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
