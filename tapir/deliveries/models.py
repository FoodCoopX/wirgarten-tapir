from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import UniqueConstraint

from tapir.core.models import TapirModel
from tapir.log.models import LogEntry
from tapir.wirgarten.models import Member, GrowingPeriod, ProductType


class Joker(TapirModel):
    class Meta:
        indexes = [models.Index(fields=["date"])]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField()


class DeliveryDonation(TapirModel):
    class Meta:
        indexes = [models.Index(fields=["date"])]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        return f"{self.member} {self.date}"


class DeliveryDayAdjustment(TapirModel):
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["growing_period", "calendar_week"],
                name="no_duplicate_week_by_growing_period",
            ),
        ]

    growing_period = models.ForeignKey(GrowingPeriod, on_delete=models.CASCADE)
    calendar_week = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(53)]
    )
    adjusted_weekday = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(6)]
    )


class JokerUsedLogEntry(LogEntry):
    template_name = "deliveries/log/joker_used_log_entry.html"

    joker = models.ForeignKey(Joker, null=True, on_delete=models.SET_NULL)
    date = models.DateField()

    def populate_joker(self, joker: Joker, actor, user):
        self.populate(actor, user)
        self.joker = joker
        self.date = joker.date
        return self


class JokerCancelledLogEntry(LogEntry):
    template_name = "deliveries/log/joker_cancelled_log_entry.html"

    date = models.DateField()

    def populate_joker(self, joker: Joker, actor, user):
        self.populate(actor, user)
        self.date = joker.date
        return self


class DeliveryDonationUsedLogEntry(LogEntry):
    template_name = "deliveries/log/delivery_donation_used_log_entry.html"

    delivery_donation = models.ForeignKey(
        DeliveryDonation, null=True, on_delete=models.SET_NULL
    )
    date = models.DateField()

    def populate_delivery_donation(
        self, delivery_donation: DeliveryDonation, actor, user
    ):
        self.populate(actor, user)
        self.delivery_donation = delivery_donation
        self.date = delivery_donation.date
        return self


class DeliveryDonationCancelledLogEntry(LogEntry):
    template_name = "deliveries/log/delivery_donation_cancelled_log_entry.html"

    date = models.DateField()

    def populate_delivery_donation(
        self, delivery_donation: DeliveryDonation, actor, user
    ):
        self.populate(actor, user)
        self.date = delivery_donation.date
        return self


class CustomCycleScheduledDeliveryWeek(TapirModel):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    growing_period = models.ForeignKey(GrowingPeriod, on_delete=models.CASCADE)
    calendar_week = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(53)]
    )

    def __str__(self):
        return f"{self.product_type.name}, {self.growing_period}, Week {self.calendar_week}"
