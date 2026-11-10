import json
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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(bid_levels__gte=1) & models.Q(bid_levels__lte=3),
                name="bidding_round_bid_levels_between_1_and_3",
            )
        ]

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
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1) & models.Q(quantity__lte=5),
                name="bid_item_quantity_between_1_and_5",
            ),
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


class BiddingRoundReplacedSubscription(BiddingRoundTapirModel):
    """Snapshot of everything contract creation hard-deletes for a replaced subscription.

    Creating contracts for a bid deletes existing, non-cancelled subscriptions for the
    same product and season. Deleting a subscription also cascades to related
    ``BreadDelivery`` rows, nulls ``SubscriptionPriceChangedLogEntry.subscription`` and
    cascades away the prior ``BiddingRoundCreatedSubscription`` link. All of this is
    snapshot here so ``delete_contracts`` can restore it and no data is lost irreversibly.
    """

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="replaced_subscriptions"
    )
    data = models.JSONField()

    def __str__(self):
        return f"{self.round} - replaced subscription snapshot"

    @classmethod
    def capture(
        cls, bidding_round, subscriptions
    ) -> "BiddingRoundReplacedSubscription":
        from django.core import serializers

        from tapir.bakery.models import BreadDelivery
        from tapir.subscriptions.models import SubscriptionPriceChangedLogEntry

        subscription_ids = [subscription.id for subscription in subscriptions]
        deliveries = list(
            BreadDelivery.objects.filter(subscription_id__in=subscription_ids)
        )
        links = list(
            BiddingRoundCreatedSubscription.objects.filter(
                subscription_id__in=subscription_ids
            )
        )
        price_logs = list(
            SubscriptionPriceChangedLogEntry.objects.filter(
                subscription_id__in=subscription_ids
            ).values_list("id", "subscription_id")
        )
        return cls.objects.create(
            round=bidding_round,
            data={
                "subscriptions": json.loads(
                    serializers.serialize("json", subscriptions)
                ),
                "deliveries": json.loads(serializers.serialize("json", deliveries)),
                "created_links": [
                    {
                        "subscription_id": link.subscription_id,
                        "round_id": link.round_id,
                        "is_bidder_contract": link.is_bidder_contract,
                    }
                    for link in links
                ],
                "price_logs": [
                    {"log_entry_id": log_entry_id, "subscription_id": subscription_id}
                    for log_entry_id, subscription_id in price_logs
                ],
            },
        )

    def restore(self) -> None:
        from django.core import serializers

        from tapir.subscriptions.models import SubscriptionPriceChangedLogEntry

        for deserialized in serializers.deserialize(
            "json", json.dumps(self.data.get("subscriptions", []))
        ):
            deserialized.save()
        for deserialized in serializers.deserialize(
            "json", json.dumps(self.data.get("deliveries", []))
        ):
            deserialized.save()
        for link in self.data.get("created_links", []):
            BiddingRoundCreatedSubscription.objects.get_or_create(
                subscription_id=link["subscription_id"],
                round_id=link["round_id"],
                defaults={"is_bidder_contract": link["is_bidder_contract"]},
            )
        for price_log in self.data.get("price_logs", []):
            SubscriptionPriceChangedLogEntry.objects.filter(
                id=price_log["log_entry_id"], subscription__isnull=True
            ).update(subscription_id=price_log["subscription_id"])
