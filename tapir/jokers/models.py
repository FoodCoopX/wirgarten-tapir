from django.db import models

from tapir.core.models import TapirModel
from tapir.wirgarten.models import Member


class Joker(TapirModel):
    class Meta:
        indexes = [models.Index(fields=["date"])]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField()
