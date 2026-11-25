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
from tapir.log.models import LogEntry
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    Product,
    ProductType,
    Subscription,
)


class BiddingRound(TapirModel):
    """One bidding round for a growing period.

    ``bidding_procedure`` selects how many amounts a member submits per share:
    ``BIDDING_ROUND_PROCEDURE_SIMPLE`` uses one to three amounts (``bid_levels``
    1-3), ``BIDDING_ROUND_PROCEDURE_BID_RANGE`` uses exactly two amounts
    (green/wish and red/pain threshold) and therefore requires ``bid_levels == 2``.
    The check constraints enforce both rules. ``contracts_created_at`` marks the
    round as evaluated: from then on the round is read-only.

    The ``locked_*`` fields freeze the evaluation base at ``average_bid_locked_at``,
    so contract creation uses exactly what the admin saw. Unlocking is only allowed
    while no contracts have been created.
    ``locked_bidder_average_per_share_per_month`` is stored as-is because that is the
    unit bids are made in; the yearly value is derived as ``month * 12``.
    ``locked_bid_range_position`` is the position (0-100) on the bidder
    distribution. ``locked_surcharge_percent`` together with
    ``locked_surcharge_on_bids``/``locked_surcharge_on_average`` records how the
    surcharge was applied.
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
    # Frozen evaluation values, so contract creation uses exactly what the admin
    # saw. Unlocking is only allowed while no contracts have been created.
    average_bid_locked_at = models.DateTimeField(null=True)
    locked_bid_range_position = models.DecimalField(
        max_digits=5, decimal_places=2, null=True
    )
    locked_bidder_average_per_share_per_month = models.DecimalField(
        max_digits=8, decimal_places=2, null=True
    )
    locked_surcharge_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    locked_surcharge_on_bids = models.BooleanField(default=False)
    locked_surcharge_on_average = models.BooleanField(default=False)
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
            models.UniqueConstraint(
                fields=["growing_period"],
                condition=models.Q(contracts_created_at__isnull=False),
                name="uniq_bidding_round_with_contracts_per_growing_period",
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
    red/pain threshold. ``entered_by_admin`` marks bids captured by an admin on
    behalf of the member. ``admin_confirmed`` is set when an admin confirms the bid;
    the timestamp is the confirmation gate for contract creation and is cleared when
    the bid amounts change. The pickup location is not stored on the bid: statistics
    and contract creation use the member's location at the growing period's start date
    (``MemberPickupLocationGetter``).
    """

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="bids"
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    entered_by_admin = models.BooleanField(default=False)
    admin_confirmed = models.DateTimeField(null=True)
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
    ``is_bidder_contract`` marks contracts created from a bid, as opposed to
    auto-renewed contracts. ``was_reused`` marks links to subscriptions that already
    existed before contract creation; ``original_quantity`` keeps their quantity from
    before the round.
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
    is_bidder_contract = models.BooleanField(default=False)
    was_reused = models.BooleanField(default=False)
    original_quantity = models.PositiveSmallIntegerField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round", "subscription"],
                name="uniq_bidding_round_created_subscription",
            )
        ]

    def __str__(self):
        return f"{self.round} - {self.subscription}"


class BiddingRoundMemberEffect(TapirModel):
    """Records what a round changed for one member, so the change can be undone.

    ``previous_*`` holds the serialized rows before the mutation, ``applied_*`` the
    rows after it. A revert restores ``previous_*`` verbatim; a change that did not
    touch anything does not create an effect.
    """

    class State(models.TextChoices):
        APPLIED = "applied", "angewendet"
        REVERSED = "reversed", "zurückgenommen"

    class Source(models.TextChoices):
        BID = "bid", "Gebot"
        AUTO_RENEWED = "auto_renewed", "Auto-Verlängerung"
        NON_BIDDER_FLOOR = "non_bidder_floor", "Nicht-Bieter-Beitrag"

    round = models.ForeignKey(
        BiddingRound, on_delete=models.CASCADE, related_name="member_effects"
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.APPLIED
    )
    source = models.CharField(max_length=24, choices=Source.choices)

    previous_subscriptions = models.JSONField(default=list)
    applied_subscriptions = models.JSONField(default=list)
    previous_contributions = models.JSONField(default=list)
    applied_contributions = models.JSONField(default=list)
    contribution_log_links = models.JSONField(default=list)
    previous_mandate_ref_ids = models.JSONField(default=list)
    created_mandate_ref_ids = models.JSONField(default=list)

    applied_at = models.DateTimeField(null=True)
    reversed_at = models.DateTimeField(null=True)
    reversed_by = models.ForeignKey(
        "accounts.TapirUser", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    reversal_reason = models.TextField(blank=True)
    divergence_overridden = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round", "member"],
                name="uniq_bidding_round_member_effect",
            )
        ]

    def __str__(self):
        return f"{self.round} - {self.member} ({self.get_state_display()})"


class BiddingRoundMemberRollbackLogEntry(LogEntry):
    template_name = "bidding_round/log/member_rollback_log_entry.html"

    round_name = models.CharField(max_length=200)
    subscriptions_deleted = models.PositiveIntegerField(default=0)
    subscriptions_restored = models.PositiveIntegerField(default=0)
    contributions_restored = models.PositiveIntegerField(default=0)
    reason = models.TextField(blank=True)
    forced = models.BooleanField(default=False)

    def populate(
        self,
        round_name=None,
        subscriptions_deleted=0,
        subscriptions_restored=0,
        contributions_restored=0,
        reason="",
        forced=False,
        *args,
        **kwargs,
    ):
        self.round_name = round_name
        self.subscriptions_deleted = subscriptions_deleted
        self.subscriptions_restored = subscriptions_restored
        self.contributions_restored = contributions_restored
        self.reason = reason
        self.forced = forced
        return super().populate(*args, **kwargs)
