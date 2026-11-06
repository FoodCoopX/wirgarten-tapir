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


class AssociationDepositAccount(TapirModel):
    member = models.OneToOneField(Member, on_delete=models.PROTECT)
    hardship_requested_at = models.DateTimeField(null=True)
    agreement_revision = models.PositiveIntegerField(default=0)
    instalment_count = models.PositiveIntegerField(default=1)
    is_individual_agreement = models.BooleanField(default=False)
    agreed_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    effective_from = models.DateField(null=True)
    collection_stopped_from = models.DateField(null=True)
    refund_requires_agreement = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(agreed_amount=None, effective_from=None)
                    | models.Q(
                        agreed_amount__isnull=False,
                        agreed_amount__gte=0,
                        effective_from__isnull=False,
                    )
                ),
                name="association_deposit_agreement_complete",
            ),
            models.CheckConstraint(
                condition=models.Q(instalment_count__gte=1),
                name="association_deposit_positive_instalments",
            ),
        ]


class AssociationDepositReceipt(TapirModel):
    account = models.ForeignKey(
        AssociationDepositAccount, on_delete=models.PROTECT, related_name="receipts"
    )
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    received_on = models.DateField()
    note = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="association_deposit_receipt_positive",
            )
        ]


class AssociationDepositReceiptCreatedLogEntry(ModelLogEntry):
    template_name = "associations/log/deposit_receipt_created.html"


class AssociationDepositRefund(TapirModel):
    account = models.ForeignKey(
        AssociationDepositAccount, on_delete=models.PROTECT, related_name="refunds"
    )
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    refunded_on = models.DateField()
    note = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="association_deposit_refund_positive",
            )
        ]


class AssociationDepositRefundCreatedLogEntry(ModelLogEntry):
    template_name = "associations/log/deposit_refund_created.html"


class AssociationDepositAgreementCreatedLogEntry(ModelLogEntry):
    template_name = "associations/log/deposit_agreement_created.html"


class AssociationDepositPaymentCreatedLogEntry(ModelLogEntry):
    template_name = "associations/log/deposit_payment_created.html"


class AssociationDepositIncreasedLogEntry(UpdateModelLogEntry):
    template_name = "associations/log/deposit_increased.html"
    excluded_fields = ["updated_at"]


class AssociationDepositMembershipChangedLogEntry(ModelLogEntry):
    template_name = "associations/log/deposit_membership_changed.html"


class AssociationDepositHardshipRequestedLogEntry(ModelLogEntry):
    template_name = "associations/log/deposit_hardship_requested.html"


class AssociationDepositAgreementAuthorizedLogEntry(ModelLogEntry):
    request_key = models.UUIDField(unique=True)
    request_hash = models.CharField(max_length=64)
    template_name = "associations/log/deposit_agreement_authorized.html"


class AssociationDepositImportedLogEntry(ModelLogEntry):
    template_name = "associations/log/deposit_imported.html"
