from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from tapir.bakery.services.breaddelivery_service import (
    ensure_bread_deliveries_for_member,
)
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

    name = models.CharField(max_length=200)
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
        indexes = [
            models.Index(fields=["pickup_location", "year", "delivery_week"]),
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
        unique_together = ("year", "delivery_week", "delivery_day", "bread")
        indexes = [
            models.Index(fields=["year", "delivery_week", "delivery_day"]),
        ]

    def __str__(self):
        return f"{self.bread.name} - Day {self.delivery_day} (Week {self.delivery_week}/{self.year})"


# class PreferredLabel(TapirModel):
#     member = models.OneToOneField(
#         Member, on_delete=models.CASCADE, related_name="preferred_labels"
#     )
#     labels = models.ManyToManyField("BreadLabel", related_name="preferred_by_members")

#     def __str__(self):
#         return f"Preferred labels for {self.member}"


class BreadDelivery(TapirModel):
    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
    )
    slot_number = models.PositiveIntegerField(
        default=1, db_index=True
    )  # 1, 2, 3, ... up to subscription.quantity
    pickup_location = models.ForeignKey(
        PickupLocation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    bread = models.ForeignKey(
        Bread,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    joker_taken = models.BooleanField(default=False)

    class Meta:
        ordering = ["year", "delivery_week", "slot_number"]
        indexes = [
            models.Index(
                fields=["year", "delivery_week"]
            ),  # Query all deliveries for a week
            models.Index(
                fields=["subscription", "year", "delivery_week"]
            ),  # Query subscription deliveries for a week
            models.Index(
                fields=["pickup_location", "year", "delivery_week"]
            ),  # Pickup list query
            models.Index(
                fields=["year", "delivery_week", "bread"]
            ),  # Aggregate bread counts
        ]

    def clean(self):
        super().clean()
        if self.bread and self.pickup_location:
            exists = BreadCapacityPickupLocation.objects.filter(
                year=self.year,
                delivery_week=self.delivery_week,
                pickup_location=self.pickup_location,
                bread=self.bread,
            ).exists()
            if not exists:
                raise ValidationError(
                    {
                        "bread": (
                            f"'{self.bread.name}' is not available at "
                            f"this pickup location in week {self.delivery_week}/{self.year}."
                        )
                    }
                )

    def save(self, *args, skip_validation=False, **kwargs):
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Delivery {self.subscription} - Week {self.delivery_week}/{self.year} #{self.slot_number}"


@receiver(post_save, sender="wirgarten.Subscription")
def on_subscription_saved(sender, instance, created, **kwargs):
    if instance.product.type.delivery_cycle != "weekly":
        return
    if not instance.start_date or not instance.end_date:
        return
    ensure_bread_deliveries_for_member(instance.member)


@receiver(post_save, sender="wirgarten.MemberPickupLocation")
def on_pickup_location_saved(sender, instance, created, **kwargs):
    ensure_bread_deliveries_for_member(instance.member)


@receiver(post_save, sender="deliveries.Joker")
def on_joker_saved(sender, instance, **kwargs):
    ensure_bread_deliveries_for_member(instance.member)


@receiver(post_delete, sender="deliveries.Joker")
def on_joker_deleted(sender, instance, **kwargs):
    ensure_bread_deliveries_for_member(instance.member)


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
        indexes = [
            models.Index(fields=["pickup_location", "year", "delivery_week"]),
        ]
        unique_together = ["pickup_location", "year", "delivery_week", "bread"]

    def __str__(self):
        return f"{self.bread.name} @ {self.pickup_location} (Week {self.delivery_week}/{self.year}): {self.count}"


class StoveSession(TapirModel):
    """Stores the baking plan for oven sessions."""

    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    delivery_day = models.PositiveIntegerField()
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
