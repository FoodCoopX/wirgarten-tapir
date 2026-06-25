from django.db import models
from django.db.models import UniqueConstraint

from tapir.core.models import TapirModel
from tapir.wirgarten.models import Member


class AssociationMembershipType(TapirModel):
    name = models.CharField(max_length=100, unique=True)
    deleted = models.BooleanField(default=False)
    description_in_bestell_wizard = models.TextField()
    order_in_bestell_wizard = models.IntegerField()

    def __str__(self):
        result = f"{self.name}"
        if self.deleted:
            result += " (deleted)"
        return result


class AssociationMembershipTypePrice(TapirModel):
    type = models.ForeignKey(AssociationMembershipType, on_delete=models.CASCADE)
    valid_from = models.DateField()
    price = models.DecimalField(decimal_places=2, max_digits=8)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["type", "valid_from"], name="unique_date")
        ]

    def __str__(self):
        return f"{self.type.name} {self.price} from:{self.valid_from}"


class AssociationMembership(TapirModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    type = models.ForeignKey(AssociationMembershipType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(null=True)

    def __str__(self):
        return f"{self.member.get_display_name()} {self.type.name} {self.start_date} -> {self.end_date}"
