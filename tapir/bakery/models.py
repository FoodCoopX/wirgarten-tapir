from django.core.validators import MinValueValidator
from django.db import models

from tapir.core.models import TapirModel
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Subscription,
)


class BreadLabel(TapirModel):
    """
    Labels for categorizing bread (e.g., 'Vollkorn', 'Sauerteig', 'Glutenfrei')
    """

    is_active = models.BooleanField(default=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Bread(TapirModel):
    """
    Bread variant with all its properties
    """

    name = models.CharField(max_length=200, unique=True)
    picture = models.ImageField(
        upload_to="breads/",
        blank=True,
        null=True,
        help_text="Image from media library with link",
    )
    description = models.TextField(
        blank=True, help_text="Description text for the bread"
    )
    weight = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="Weight in grams",
    )
    labels = models.ManyToManyField("BreadLabel", related_name="breads", blank=True)
    pieces_per_stove_layer = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of possible pieces per stove layer (e.g., [10, 11, 12] or [22, 24])",
    )
    one_batch_can_be_baked_in_more_than_one_stove = models.BooleanField(
        default=False
    )  # this because the dough can be put in the fridge
    min_pieces = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Minimum number of pieces that should be baked for this bread on a baking day (e.g., to ensure that there are enough pieces for walk-in customers)",
    )
    max_pieces = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Maximum number of pieces that should be baked for this bread on a baking day (e.g., to limit the amount of bread that can be ordered for this bread)",
    )
    min_remaining_pieces = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Minimum amount of breads that should remain available for this bread on a baking day (e.g., for walk-in customers)",
    )

    # Admin fields
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Ingredient(TapirModel):
    """
    Ingredient that can be used in bread recipes
    """

    is_active = models.BooleanField(default=True)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_organic = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class BreadContent(TapirModel):
    """
    Junction table linking breads to ingredients with amounts
    """

    bread = models.ForeignKey(
        "Bread", on_delete=models.CASCADE, related_name="contents"
    )
    ingredient = models.ForeignKey(
        "Ingredient",
        on_delete=models.PROTECT,
        related_name="bread_uses",
    )
    amount = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="Amount in grams or percentage",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("bread", "ingredient")

    def __str__(self):
        return f"{self.bread.name} - {self.ingredient.name}"


class BreadCapacityPickupLocation(TapirModel):
    """
    Capacity of how many breads can be delivered to each pickup location on each delivery day
    """

    year = models.PositiveIntegerField(help_text="Year for which this capacity applies")
    delivery_week = models.PositiveIntegerField(help_text="Delivery week number (1-53)")
    pickup_location = models.ForeignKey(
        PickupLocation,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="bread_capacities",
    )
    bread = models.ForeignKey(
        "Bread",
        on_delete=models.CASCADE,
        related_name="capacity_entries",
    )
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Maximum number of breads of this type that can be delivered to this pickup location on this delivery day",
    )

    class Meta:
        unique_together = ("pickup_location", "year", "delivery_week", "bread")
        # The unique constraint indexes every lookup that starts with the
        # station. This one covers the solver's "all capacities of a week".
        indexes = [
            models.Index(fields=["year", "delivery_week"]),
        ]

    def __str__(self):
        return f"{self.bread.name} @ {self.pickup_location} {self.capacity} (Week {self.delivery_week}/{self.year})"


class AvailableBreadsForDeliveryDay(TapirModel):
    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    delivery_day = models.PositiveIntegerField(
        help_text="Day of week for delivery (0=Monday, 6=Sunday)"
    )
    bread = models.ForeignKey(
        "Bread", on_delete=models.CASCADE, related_name="delivery_days"
    )

    class Meta:
        # No indexes: the unique constraint indexes exactly these three columns
        # plus the bread, so an index on the prefix would only cost writes.
        unique_together = ("year", "delivery_week", "delivery_day", "bread")

    def __str__(self):
        return f"{self.bread.name} - Day {self.delivery_day} (Week {self.delivery_week}/{self.year})"


class BreadDelivery(TapirModel):
    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
    )
    # No db_index: a slot number is only ever read together with its
    # subscription and week, which the unique constraint below indexes.
    slot_number = models.PositiveIntegerField(
        default=1
    )  # 1, 2, 3, ... up to subscription.quantity
    bread = models.ForeignKey(
        Bread,
        # PROTECT so that deleting a bread cannot wipe the members' choices
        # across every week. Deactivate a bread with is_active instead.
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["year", "delivery_week", "slot_number"]
        unique_together = ("subscription", "year", "delivery_week", "slot_number")
        indexes = [
            models.Index(
                fields=["year", "delivery_week", "bread"]
            ),  # All deliveries of a week, and bread counts within it
        ]

    def __str__(self):
        return f"Delivery {self.subscription} - Week {self.delivery_week}/{self.year} #{self.slot_number}"


class PreferredBread(TapirModel):
    member = models.OneToOneField(
        Member, on_delete=models.CASCADE, related_name="preferred_breads"
    )
    breads = models.ManyToManyField("Bread", related_name="preferred_by_members")

    def __str__(self):
        return f"Preferred breads for {self.member}"


class BreadsPerPickupLocationPerWeek(TapirModel):
    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    pickup_location = models.ForeignKey(
        PickupLocation,
        on_delete=models.CASCADE,
        related_name="bread_counts",
    )
    bread = models.ForeignKey(
        "Bread",
        on_delete=models.CASCADE,
        related_name="pickup_location_counts",
    )
    count = models.PositiveIntegerField(default=0)

    class Meta:
        # As on BreadCapacityPickupLocation: the unique constraint indexes
        # everything that starts with the station, and the query that reads
        # this table is "the whole week".
        indexes = [
            models.Index(fields=["year", "delivery_week"]),
        ]
        unique_together = ["pickup_location", "year", "delivery_week", "bread"]

    def __str__(self):
        return f"{self.bread.name} @ {self.pickup_location} (Week {self.delivery_week}/{self.year}): {self.count}"


class BreadsToBakePerWeek(TapirModel):
    """
    How many of each bread the solver decided to bake, and how many of those
    are surplus beyond what members receive.

    Persisted rather than derived: a bread with fixed_pieces occupies no stove
    layers, so the quantity cannot be recovered by summing StoveSession.
    """

    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    # Null for a whole-week plan, set for a plan made day by day.
    delivery_day = models.PositiveIntegerField(null=True, blank=True)
    bread = models.ForeignKey(
        "Bread", on_delete=models.CASCADE, related_name="quantities_to_bake"
    )
    quantity = models.PositiveIntegerField(help_text="Total pieces to bake")
    remaining = models.PositiveIntegerField(
        default=0, help_text="Pieces beyond what the deliveries need"
    )

    class Meta:
        unique_together = ("year", "delivery_week", "delivery_day", "bread")
        indexes = [models.Index(fields=["year", "delivery_week", "delivery_day"])]
        constraints = [
            # unique_together does not cover the whole-week rows: NULL never
            # equals NULL, so the constraint above admits any number of them.
            models.UniqueConstraint(
                fields=["year", "delivery_week", "bread"],
                condition=models.Q(delivery_day__isnull=True),
                name="unique_breads_to_bake_per_whole_week",
            )
        ]

    def __str__(self):
        return f"{self.bread.name}: {self.quantity} (Week {self.delivery_week}/{self.year})"


class StoveSession(TapirModel):
    """Stores the baking plan for oven sessions."""

    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    # Null for a whole-week plan, set for a plan made day by day.
    delivery_day = models.PositiveIntegerField(null=True, blank=True)
    session_number = models.PositiveIntegerField()  # 1, 2, 3, ...
    layer_number = models.PositiveIntegerField()  # 1, 2, 3, 4
    bread = models.ForeignKey(
        "Bread",
        on_delete=models.CASCADE,
        null=True,  # Null if layer is empty
        related_name="stove_sessions",
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["session_number", "layer_number"]
        unique_together = [
            "year",
            "delivery_week",
            "delivery_day",
            "session_number",
            "layer_number",
        ]
        constraints = [
            # unique_together does not cover the whole-week rows: NULL never
            # equals NULL, so the constraint above admits any number of them.
            models.UniqueConstraint(
                fields=["year", "delivery_week", "session_number", "layer_number"],
                condition=models.Q(delivery_day__isnull=True),
                name="unique_stove_session_per_whole_week",
            )
        ]

    def __str__(self):
        bread_name = self.bread.name if self.bread else "Empty"
        return f"Session {self.session_number} Layer {self.layer_number} - {bread_name}"


class PreferenceSatisfactionLogging(TapirModel):
    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    delivery_day = models.PositiveIntegerField()
    pickup_location = models.ForeignKey(
        PickupLocation,
        on_delete=models.CASCADE,
        related_name="preference_satisfaction_logs",
    )
    percentage_satisfied = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage of deliveries that matched at least one preferred bread label",
    )

    class Meta:
        unique_together = ["year", "delivery_week", "delivery_day", "pickup_location"]

    def __str__(self):
        return f"Satisfaction {self.pickup_location} Day {self.delivery_day} (Week {self.delivery_week}/{self.year}): {self.percentage_satisfied}%"


# this model is only filled in case there are overrides to the defaults in the bread model
# or if fixed_pieces or max_pieces need to be given for a specific delivery day
class BreadSpecificsPerDeliveryDay(TapirModel):
    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    delivery_day = models.PositiveIntegerField()
    bread = models.ForeignKey(
        "Bread",
        on_delete=models.CASCADE,
        related_name="specifics_per_delivery_day",
    )
    min_pieces = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Minimum number of pieces that should be baked for this bread on this delivery day (e.g., to ensure that there are enough pieces for walk-in customers)",
    )
    max_pieces = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Maximum number of pieces that should be baked for this bread on this delivery day (e.g., to limit the amount of bread that can be ordered for this bread)",
    )
    min_remaining_pieces = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Minimum amount of breads that should remain available for this bread on this delivery day (e.g., for walk-in customers)",
    )
    fixed_pieces = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="If set, exactly this number of pieces should be baked for this bread on this delivery day (overrides min/max)",
    )

    class Meta:
        indexes = [
            models.Index(fields=["year", "delivery_week", "delivery_day"]),
        ]
        unique_together = ["year", "delivery_week", "delivery_day", "bread"]

    def __str__(self):
        return f"{self.bread.name} specifics for Day {self.delivery_day} (Week {self.delivery_week}/{self.year})"
