from django.db import models

from tapir.core.models import TapirModel


class AssociationMembershipType(TapirModel):
    name = models.CharField(max_length=100, unique=True)
    deleted = models.BooleanField(default=False)


class AssociationMembershipTypePrice(TapirModel):
    type = models.ForeignKey(AssociationMembershipType, on_delete=models.CASCADE)
    valid_from = models.DateField()
    price = models.DecimalField(decimal_places=2, max_digits=8)
