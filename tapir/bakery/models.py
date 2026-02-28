from datetime import datetime, timedelta

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

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
    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
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

    # bakery fields
    # breads_per_layer = models.PositiveIntegerField(blank=True, null=True)
    # max_breads_per_baking_day = models.PositiveIntegerField(blank=True, null=True)
    # min_breads_per_baking_day = models.PositiveIntegerField(blank=True, null=True)
    # step_size = models.PositiveIntegerField(blank=True, null=True)
    # breads_per_one_dough = models.IntegerField(blank=True, null=True)


class Ingredient(TapirModel):
    """
    Ingredient that can be used in bread recipes
    """

    is_active = models.BooleanField(default=True)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_organic = models.BooleanField(default=False)


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
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Amount in grams or percentage",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("bread", "ingredient")


class BreadCapacityPickupLocation(TapirModel):
    """
    Capacity of how many breads can be delivered to each pickup location on each delivery day
    """

    year = models.PositiveIntegerField(help_text="Year for which this capacity applies")
    delivery_week = models.PositiveIntegerField(help_text="Delivery week number (1-53)")
    pickup_location = models.ForeignKey(
        PickupLocation,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="bread_capacities",
        help_text="The pickup location this capacity applies to (redundant but useful for queries)",
    )
    bread = models.ForeignKey(
        "Bread",
        on_delete=models.CASCADE,
        related_name="capacity_entries",
    )
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Maximum number of breads of this label that can be delivered to this pickup location on this delivery day",
    )

    class Meta:
        unique_together = ("pickup_location", "year", "delivery_week", "bread")


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


class PreferredLabel(TapirModel):
    member = models.OneToOneField(
        Member, on_delete=models.CASCADE, related_name="preferred_labels"
    )
    labels = models.ManyToManyField("BreadLabel", related_name="preferred_by_members")


class BreadDelivery(TapirModel):
    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
    )
    slot_number = models.PositiveIntegerField(
        default=1
    )  # 1, 2, 3, ... up to subscription.quantity
    pickup_location = models.ForeignKey(
        PickupLocation,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    bread = models.ForeignKey(
        Bread,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["year", "delivery_week", "slot_number"]


def get_weeks_in_range(start_date, end_date):
    """
    Generator that yields (year, week_number) tuples for all weeks between start_date and end_date
    """
    current_date = start_date
    while current_date <= end_date:
        iso_calendar = current_date.isocalendar()
        yield (iso_calendar[0], iso_calendar[1])  # (year, week)
        current_date += timedelta(weeks=1)


@receiver(post_save, sender="wirgarten.Subscription")
def sync_bread_deliveries_with_subscription(sender, instance, created, **kwargs):
    """
    When a subscription is created or updated, synchronize all BreadDelivery records
    for current and future weeks within the subscription period
    """
    if not instance.start_date or not instance.end_date:
        return

    # Get current date
    now = datetime.now().date()

    # Start from current week or subscription start, whichever is later
    start_date = max(now, instance.start_date)
    end_date = instance.end_date

    # If subscription has ended, delete all deliveries
    if start_date > end_date:
        BreadDelivery.objects.filter(
            subscription=instance,
        ).delete()
        return

    # Get member's pickup location if it exists
    member_pickup_location = instance.member.get_pickup_location(now)

    # Get all weeks in the subscription period (current + future)
    weeks_in_period = list(get_weeks_in_range(start_date, end_date))

    for year, week in weeks_in_period:
        # Get existing deliveries for this week
        existing_deliveries = BreadDelivery.objects.filter(
            subscription=instance, year=year, delivery_week=week
        ).order_by("slot_number")

        existing_count = existing_deliveries.count()
        target_quantity = instance.quantity

        # If we need more slots, create them
        if existing_count < target_quantity:
            for slot_number in range(existing_count + 1, target_quantity + 1):
                BreadDelivery.objects.create(
                    subscription=instance,
                    year=year,
                    delivery_week=week,
                    slot_number=slot_number,
                    pickup_location=member_pickup_location,
                    bread=None,
                )

        # If we have too many slots, remove the extras
        elif existing_count > target_quantity:
            deliveries_to_remove = existing_deliveries[target_quantity:]
            for delivery in deliveries_to_remove:
                delivery.delete()

    # Delete any deliveries outside the subscription period
    BreadDelivery.objects.filter(subscription=instance).exclude(
        year__in=[w[0] for w in weeks_in_period],
        delivery_week__in=[w[1] for w in weeks_in_period],
    ).delete()


@receiver(post_delete, sender="wirgarten.Subscription")
def delete_bread_deliveries_on_subscription_delete(sender, instance, **kwargs):
    """
    When a subscription is deleted, delete all associated bread deliveries
    """
    BreadDelivery.objects.filter(subscription=instance).delete()


@receiver(post_save, sender="wirgarten.MemberPickupLocation")
def update_bread_deliveries_pickup_location(sender, instance, created, **kwargs):
    """
    When a member's pickup location changes, update all current and future BreadDelivery records
    """
    # Get current date
    now = datetime.now().date()
    current_iso = now.isocalendar()
    current_year, current_week = current_iso[0], current_iso[1]

    # Update all bread deliveries for this member for current and future weeks
    BreadDelivery.objects.filter(
        subscription__member=instance.member, year__gte=current_year
    ).filter(
        models.Q(year__gt=current_year)
        | models.Q(year=current_year, delivery_week__gte=current_week)
    ).update(pickup_location=instance.pickup_location)


class PreferredBread(TapirModel):
    member = models.OneToOneField(
        Member, on_delete=models.CASCADE, related_name="preferred_breads"
    )
    breads = models.ManyToManyField("Bread", related_name="preferred_by_members")


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
