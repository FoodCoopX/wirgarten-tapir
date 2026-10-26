import uuid

from django.db import models

from tapir.bidding_round.config import (
    CONFIGURATION,
    OPTIONS_BIDDING_ROUND_PROCEDURE,
    OPTIONS_BIDDING_ROUND_STATUS,
    SIMPLE,
)
from tapir.core.models import TapirModel
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    PickupLocation,
    Product,
    ProductType,
    Subscription,
)


class BiddingRoundTapirModel(TapirModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )

    class Meta:
        abstract = True


class BiddingRound(BiddingRoundTapirModel):
    growing_period = models.ForeignKey(GrowingPeriod, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20, choices=OPTIONS_BIDDING_ROUND_STATUS, default=CONFIGURATION
    )
    bidding_procedure = models.CharField(
        max_length=20, choices=OPTIONS_BIDDING_ROUND_PROCEDURE, default=SIMPLE
    )
    # Number of bid levels a member submits in a simple round (1-3). Level i is
    # stored in BidItem.amount_i. The traffic_light procedure always uses all three levels
    # as green/yellow/red anchors instead.
    bid_levels = models.PositiveSmallIntegerField(default=1)
    start_at = models.DateTimeField(null=True)
    end_at = models.DateTimeField(null=False)
    include_auto_renewed = models.BooleanField(default=True)
    contracts_created_at = models.DateTimeField(null=True)
    comment = models.TextField(blank=True)
    # Locked average bid: the position on the 0/50/100 axis and the surcharge chosen
    # in the evaluation are frozen here so that contract creation uses exactly the
    # values shown in the evaluation. Unlocking is only allowed while no contracts
    # have been created (contracts_created_at is None).
    average_bid_locked_at = models.DateTimeField(null=True)
    locked_traffic_light_position = models.DecimalField(
        max_digits=5, decimal_places=2, null=True
    )
    locked_average_bid_per_share_per_month = models.DecimalField(
        max_digits=8, decimal_places=2, null=True
    )
    locked_average_bid_per_share_per_year = models.DecimalField(
        max_digits=8, decimal_places=2, null=True
    )
    locked_bidder_average_per_share_per_month = models.DecimalField(
        max_digits=8, decimal_places=2, null=True
    )
    locked_bidder_average_per_share_per_year = models.DecimalField(
        max_digits=8, decimal_places=2, null=True
    )
    locked_surcharge_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    locked_surcharge_on_bids = models.BooleanField(default=False)
    locked_surcharge_on_average = models.BooleanField(default=False)

    @property
    def is_average_bid_locked(self) -> bool:
        return self.average_bid_locked_at is not None

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class BiddingRoundProduct(BiddingRoundTapirModel):
    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="products"
    )
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    target_amount_per_year = models.DecimalField(
        max_digits=12, decimal_places=2, null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["round"], name="uniq_round_product")
        ]

    def __str__(self):
        return f"{self.round} - {self.product_type}"


class BiddingRoundProductPrice(BiddingRoundTapirModel):
    round_product = models.ForeignKey(
        BiddingRoundProduct, on_delete=models.CASCADE, related_name="prices"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # Values are entered per product (= share size) and apply 1:1, without any
    # scaling by the product price size.
    reference_value = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    min_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round_product", "product"], name="uniq_round_product_price"
            )
        ]

    def __str__(self):
        return f"{self.round_product} - {self.product}"


class Bid(BiddingRoundTapirModel):
    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="bids"
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    pickup_location = models.ForeignKey(
        PickupLocation, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    entered_by_admin = models.BooleanField(default=False)
    admin_confirmed = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round", "member"], name="uniq_round_member"
            )
        ]

    def __str__(self):
        return f"{self.round} - {self.member}"


class BidItem(BiddingRoundTapirModel):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name="items")
    round_product = models.ForeignKey(BiddingRoundProduct, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField()
    # Bid levels, ascending. For a simple round with N levels only amount_1..amount_N
    # are set; for the traffic_light procedure amount_1/amount_2/amount_3 are green
    # (wish) / yellow (satisfied) / red (pain threshold).
    amount_1 = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    amount_2 = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    amount_3 = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bid", "round_product"], name="uniq_bid_round_product"
            )
        ]

    def __str__(self):
        return f"{self.bid} - {self.product} ({self.amount_2})"


class BiddingRoundCreatedSubscription(BiddingRoundTapirModel):
    """Links a subscription created by a bidding round to that round, so the created
    contracts can be listed and deleted again."""

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="created_subscriptions"
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="+"
    )
    is_bidder_contract = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.round} - {self.subscription}"
