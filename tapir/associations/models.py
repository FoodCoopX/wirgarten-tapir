from django.db import models
from django.db.models import UniqueConstraint

from tapir.accounts.models import TapirUser
from tapir.core.models import TapirModel
from tapir.log.models import LogEntry, UpdateModelLogEntry, ModelLogEntry
from tapir.wirgarten.models import Member

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


class AssociationDeposit(TapirModel):
    member = models.OneToOneField(Member, on_delete=models.PROTECT)
    agreed_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    minimum_at_agreement = models.DecimalField(
        max_digits=8, decimal_places=2, null=True
    )
    hardship_pending = models.BooleanField(default=False)
    exception_authorized = models.BooleanField(default=False)
    effective_from = models.DateField(null=True)
    cancellation_date = models.DateField(null=True)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(agreed_amount__gte=0) | models.Q(agreed_amount=None),
                name="deposit_nonnegative_agreement",
            ),
            models.CheckConstraint(
                condition=models.Q(hardship_pending=False)
                | models.Q(agreed_amount=None),
                name="deposit_pending_without_debt",
            ),
        ]


class AssociationDepositOperation(TapirModel):
    deposit = models.ForeignKey(
        AssociationDeposit, on_delete=models.PROTECT, related_name="operations"
    )
    request_id = models.CharField(max_length=100)
    payload = models.JSONField()
    changes = models.JSONField(default=dict)
    actor = models.ForeignKey(TapirUser, on_delete=models.SET_NULL, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deposit", "request_id"], name="unique_deposit_request"
            ),
            models.UniqueConstraint(
                fields=["request_id"],
                condition=models.Q(request_id__startswith="import:"),
                name="unique_deposit_import_reference",
            ),
        ]


class AssociationDepositBooking(TapirModel):
    class Kind(models.TextChoices):
        RECEIPT = "receipt", "Extern eingegangen"
        IMPORT = "import", "Historische Einzahlung"
        REFUND = "refund", "Extern zurückgezahlt"
        REVERSAL = "reversal", "Rücklastschrift / Korrektur"

    deposit = models.ForeignKey(
        AssociationDeposit, on_delete=models.PROTECT, related_name="bookings"
    )
    operation = models.OneToOneField(
        AssociationDepositOperation, on_delete=models.PROTECT
    )
    kind = models.CharField(max_length=20, choices=Kind)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    date = models.DateField()
    note = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="deposit_booking_positive"
            )
        ]


class AssociationDepositLogEntry(LogEntry):
    template_name = "associations/log/deposit_changed.html"
    operation = models.OneToOneField(
        AssociationDepositOperation, on_delete=models.PROTECT
    )
    description = models.TextField()
