from django.db import models

from tapir.core.models import TapirModel
from tapir.wirgarten.models import Member


class SolidarityContribution(TapirModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    start_date = models.DateField()
    end_date = models.DateField()
