from django.db import models
from django.db.models import UniqueConstraint

from tapir.accounts.models import TapirUser
from tapir.core.models import TapirModel
from tapir.log.models import LogEntry, UpdateModelLogEntry, ModelLogEntry
from tapir.wirgarten.models import Member, Payment

ASSOCIATION_MEMBERSHIP_TYPE_NAME_MAX_LENGTH = 100


class AssociationMembershipType(TapirModel):
    name = models.CharField(
        max_length=ASSOCIATION_MEMBERSHIP_TYPE_NAME_MAX_LENGTH, unique=True
    )
    deleted = models.BooleanField(default=False)
    description_in_bestell_wizard = models.TextField()
    order_in_bestell_wizard = models.IntegerField()
    hidden_in_bestell_wizard = models.BooleanField(default=False)

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
    cancellation_ts = models.DateTimeField(null=True)
    membership_ended_mail_sent_on = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return f"{self.member.get_display_name()} {self.type.name} {self.start_date} -> {self.end_date}"


class AssociationDeposit(TapirModel):
    imported_outstanding_amount = models.DecimalField(
        max_digits=8, decimal_places=2, null=True
    )
    opening_balance = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    membership = models.ForeignKey(
        AssociationMembership,
        null=True,
        on_delete=models.SET_NULL,
        related_name="deposits",
    )
    payment = models.OneToOneField(
        Payment, null=True, on_delete=models.CASCADE, related_name="association_deposit"
    )


class AssociationDepositAgreedLogEntry(LogEntry):
    template_name = "associations/log/deposit_agreed.html"

    amount = models.DecimalField(max_digits=8, decimal_places=2)


class AssociationMembershipDeletedLogEntry(LogEntry):
    template_name = "associations/log/membership_deleted.html"

    type_name = models.CharField(max_length=ASSOCIATION_MEMBERSHIP_TYPE_NAME_MAX_LENGTH)
    start_date = models.DateField()
    end_date = models.DateField(null=True)

    def populate_membership(self, membership: AssociationMembership, actor: TapirUser):
        self.populate(actor=actor, user=membership.member)
        self.type_name = membership.type.name
        self.start_date = membership.start_date
        self.end_date = membership.end_date

        return self


class AssociationMembershipUpdatedLogEntry(UpdateModelLogEntry):
    template_name = "associations/log/membership_updated.html"
    excluded_fields = ["updated_at"]


class AssociationMembershipCreatedLogEntry(ModelLogEntry):
    template_name = "associations/log/membership_created.html"

    type_name = models.CharField(max_length=ASSOCIATION_MEMBERSHIP_TYPE_NAME_MAX_LENGTH)

    def populate_membership(
        self, membership: AssociationMembership, actor: TapirUser | None
    ):
        self.populate(model=membership, user=membership.member, actor=actor)
        self.type_name = membership.type.name

        return self
