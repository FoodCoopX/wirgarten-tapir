from datetime import datetime, timedelta

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
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
        indexes = [
            models.Index(fields=["pickup_location", "year", "delivery_week"]),
        ]


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
            ),  # Abholliste query
            models.Index(
                fields=["year", "delivery_week", "bread"]
            ),  # Aggregate bread counts
        ]


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
    # Only sync for weekly subscriptions
    if instance.product.type.delivery_cycle != "WEEKLY":
        return

    # Only sync if subscription has valid dates
    if not instance.start_date or not instance.end_date:
        return

    now = datetime.now().date()

    start_date = instance.start_date
    end_date = instance.end_date

    member_pickup_location = instance.member.get_pickup_location(now)

    weeks_in_period = list(get_weeks_in_range(start_date, end_date))

    created_count = 0
    deleted_count = 0
    skipped_count = 0

    for year, week in weeks_in_period:
        existing_deliveries = BreadDelivery.objects.filter(
            subscription=instance, year=year, delivery_week=week
        ).order_by("slot_number")

        existing_count = existing_deliveries.count()
        target_quantity = instance.quantity

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
                created_count += 1
        elif existing_count > target_quantity:
            deliveries_to_remove = existing_deliveries[target_quantity:]
            for delivery in deliveries_to_remove:
                delivery.delete()
                deleted_count += 1
        else:
            skipped_count += 1

    # Delete any deliveries outside the subscription period
    valid_year_weeks = set(weeks_in_period)
    all_deliveries = BreadDelivery.objects.filter(subscription=instance)
    ids_to_keep = []
    for delivery in all_deliveries:
        if (delivery.year, delivery.delivery_week) in valid_year_weeks:
            ids_to_keep.append(delivery.id)

    outside = all_deliveries.exclude(id__in=ids_to_keep)
    outside.delete()


@receiver(post_save, sender="wirgarten.MemberPickupLocation")
def update_bread_deliveries_pickup_location(sender, instance, created, **kwargs):
    """
    When a member's pickup location changes or is created, update all current and future BreadDelivery records.
    If the member has subscriptions but no deliveries yet, trigger their creation.
    """

    now = datetime.now().date()
    current_iso = now.isocalendar()
    current_year, current_week = current_iso[0], current_iso[1]

    # Check what deliveries exist for this member
    all_member_deliveries = BreadDelivery.objects.filter(
        subscription__member=instance.member
    )

    # Check what the filter would match
    future_deliveries = all_member_deliveries.filter(year__gte=current_year).filter(
        models.Q(year__gt=current_year)
        | models.Q(year=current_year, delivery_week__gte=current_week)
    )
    print(f"   📦 Future deliveries (to update): {future_deliveries.count()}")

    if future_deliveries.count() > 0:
        print(
            f"   First future delivery: Year={future_deliveries.first().year}, Week={future_deliveries.first().delivery_week}"
        )
        print(
            f"   Last future delivery: Year={future_deliveries.last().year}, Week={future_deliveries.last().delivery_week}"
        )

    # Do the update
    updated = future_deliveries.update(pickup_location=instance.pickup_location)

    if created or updated == 0:
        print("   ➡️  YES - triggering subscription sync")

        active_subscriptions = Subscription.objects.filter(
            member=instance.member,
            end_date__gte=now,
        )
        print(f"   Active subscriptions found: {active_subscriptions.count()}")

        for subscription in active_subscriptions:
            print(f"\n   ➡️  Triggering sync for subscription {subscription.id}")
            print(
                f"       Period: {subscription.start_date} to {subscription.end_date}"
            )
            sync_bread_deliveries_with_subscription(
                sender=Subscription, instance=subscription, created=False, kwargs={}
            )
    else:
        print("   ➡️  NO - deliveries were updated directly, no sync needed")


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

    class Meta:
        indexes = [
            models.Index(fields=["pickup_location", "year", "delivery_week"]),
        ]


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


# this model is only field in case there are overrides to the defaults in the bread model
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
