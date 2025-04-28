from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import UniqueConstraint

from tapir.core.models import TapirModel
from tapir.wirgarten.models import Member, GrowingPeriod


class Joker(TapirModel):
    class Meta:
        indexes = [models.Index(fields=["date"])]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField()


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
