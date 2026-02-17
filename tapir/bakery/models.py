from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from tapir.core.models import TapirModel
from tapir.wirgarten.models import Member, PickupLocationOpeningTime, Subscription


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

    # Admin fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


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


class BakeryUserProfile(TapirModel):
    """
    Additional bakery-specific user data
    Extends Member without modifying it
    """

    member = models.OneToOneField(
        Member, on_delete=models.CASCADE, related_name="bakery_profile"
    )

    # Pseudonym feature
    pseudonym = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nickname/Pseudonym for member list and subscription deliveries",
    )

    # Other bakery preferences
    preferred_bread_labels = models.ManyToManyField(
        "BreadLabel", blank=True, related_name="preferred_by_users"
    )

    class Meta:
        verbose_name = "Bakery User Profile"
        verbose_name_plural = "Bakery User Profiles"

    def __str__(self):
        display_name = self.pseudonym or self.member.get_display_name()
        return f"{self.member.member_no} - {display_name}"

    def get_display_name(self) -> str:
        """
        Returns pseudonym if set and active, otherwise member's real name
        """
        if self.pseudonym:
            return self.pseudonym
        return self.member.get_display_name()


class BakeryConfiguration(TapirModel):
    """
    Singleton model for bakery-wide configuration settings
    """

    pseudonyms_can_be_used = models.BooleanField(
        default=False,
        help_text="Whether pseudonyms can be used in member lists and deliveries",
    )
    members_can_choose_breads = models.BooleanField(
        default=True,
        help_text="Whether members can choose their preferred bread types",
    )
    pickup_stations_can_be_chosen_per_share_not_just_per_member = models.BooleanField(
        default=False,
        help_text="Whether pickup stations can be chosen per share instead of just per member",
    )
    days_backing_day_is_before_delivery_day = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Number of days before delivery day that the backing day is (e.g., 2 means backing day is 2 days before delivery day)",
    )
    days_choosing_day_is_before_backing_day = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Number of days before backing day that the choosing day is (e.g., 2 means choosing day is 2 days before backing day)",
    )
    # Example setting: deadline for changing pseudonym before next delivery
    days_pseudonym_can_be_changed_before_delivery = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Number of days before delivery day that pseudonym can be changed",
    )

    class Meta:
        verbose_name = "Bakery Configuration"
        verbose_name_plural = "Bakery Configuration"

    def __str__(self):
        return "Bakery Configuration"


class BreadCapacityPickupStation(TapirModel):
    """
    Capacity of how many breads can be delivered to each pickup station on each delivery day
    """

    year = models.PositiveIntegerField(help_text="Year for which this capacity applies")
    delivery_week = models.PositiveIntegerField(help_text="Delivery week number (1-53)")
    pickup_station_day = models.ForeignKey(
        PickupLocationOpeningTime,
        on_delete=models.CASCADE,
        related_name="bread_capacities",
        help_text="The pickup station and day this capacity applies to",
    )
    bread = models.ForeignKey(
        "Bread",
        on_delete=models.CASCADE,
        related_name="capacity_entries",
    )
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Maximum number of breads of this label that can be delivered to this pickup station on this delivery day",
    )

    class Meta:
        unique_together = ("pickup_station_day", "year", "delivery_week", "bread")


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


class BreadDelivery(TapirModel):
    year = models.PositiveIntegerField()
    delivery_week = models.PositiveIntegerField()
    delivery_day = models.PositiveIntegerField(
        help_text="Day of week for delivery (0=Monday, 6=Sunday)"
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="weekly_bread_selections",
    )
    bread = models.ForeignKey(
        "Bread", on_delete=models.CASCADE, related_name="weekly_selections"
    )

    def clean(self):
        # Check that total breads for this week don't exceed subscription quantity
        existing = BreadDelivery.objects.filter(
            year=self.year,
            delivery_week=self.delivery_week,
            delivery_day=self.delivery_day,
            subscription=self.subscription,
        ).exclude(pk=self.pk)

        if existing.count() >= self.subscription.quantity:
            raise ValidationError(
                f"Subscription allows max {self.subscription.quantity} bread(s) per week"
            )
