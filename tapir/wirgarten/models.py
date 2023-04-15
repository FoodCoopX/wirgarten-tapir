import datetime
from functools import partial

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint, Index, F, Sum, Case, When
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from localflavor.generic.models import IBANField

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.core.models import TapirModel
from tapir.log.models import UpdateModelLogEntry, LogEntry
from tapir.wirgarten.constants import DeliveryCycle, NO_DELIVERY
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.utils import format_date


class PickupLocation(TapirModel):
    """
    This is a place where a Member can pick up his/her products.
    """

    name = models.TextField(_("Name"), max_length=150)
    coords_lon = models.DecimalField(
        _("Coordinates Longitude"), decimal_places=10, max_digits=12
    )
    coords_lat = models.DecimalField(
        _("Coordinates Latitude"), decimal_places=10, max_digits=12
    )
    street = models.CharField(_("Street and house number"), max_length=150)
    street_2 = models.CharField(_("Extra address line"), max_length=150, blank=True)
    postcode = models.CharField(_("Postcode"), max_length=32)
    city = models.CharField(_("City"), max_length=50)
    info = models.CharField(_("Additional info like opening times"), max_length=150)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name", "coords_lat", "coords_lon"],
                name="unique_location",
            ),
        ]

    def __str__(self):
        return self.name


class GrowingPeriod(TapirModel):
    """
    The growing period for the WirGarten site. Usually the growing period starts on 1st of March, and ends in the end of next February.
    """

    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{format_date(self.start_date)} - {format_date(self.end_date)}"


class ProductType(TapirModel):
    """
    This is the type of the product, e.g. harvest share, chicken share, ...
    """

    name = models.CharField(max_length=128, null=False, verbose_name=_("Produkt Name"))
    delivery_cycle = models.CharField(
        max_length=16,
        choices=DeliveryCycle,
        null=False,
        default=NO_DELIVERY,
        verbose_name=_("Lieferzyklus"),
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name"],
                name="unique_product_Type",
            )
        ]

    def __str__(self):
        return self.name


class PickupLocationCapability(TapirModel):
    """
    The availability of a product at a certain pickup location.
    """

    product_type = models.ForeignKey(
        ProductType, null=False, on_delete=models.DO_NOTHING
    )
    pickup_location = models.ForeignKey(
        PickupLocation, null=False, on_delete=models.DO_NOTHING
    )


class DeliveryExceptionPeriod(TapirModel):
    """
    Defines a period in which no delivery of a certain product takes place.
    """

    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    product_type = models.ForeignKey(
        ProductType, null=True, on_delete=models.DO_NOTHING
    )
    comment = models.CharField(max_length=128, null=False, default="")


class ProductCapacity(TapirModel):
    """
    This is used to configure how much of a ProductType can be sold in a growing period.
    """

    period = models.ForeignKey(GrowingPeriod, null=False, on_delete=models.DO_NOTHING)
    product_type = models.ForeignKey(
        ProductType, null=False, on_delete=models.DO_NOTHING
    )
    capacity = models.DecimalField(decimal_places=2, max_digits=20, null=False)

    indexes = [Index(fields=["period"], name="idx_productcapacity_period")]


class Member(TapirUser):
    """
    A member of WirGarten. Usually a member has coop shares and optionally other subscriptions.
    """

    account_owner = models.CharField(_("Account owner"), max_length=150, null=True)
    iban = IBANField(_("IBAN"), null=True)
    sepa_consent = models.DateTimeField(_("SEPA Consent"), null=True)
    pickup_location = models.ForeignKey(
        PickupLocation, on_delete=models.DO_NOTHING, null=True
    )
    withdrawal_consent = models.DateTimeField(
        _("Right of withdrawal consent"), null=True
    )
    privacy_consent = models.DateTimeField(_("Privacy consent"), null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    member_no = models.IntegerField(_("Mitgliedsnummer"), unique=True, null=True)

    @classmethod
    def generate_member_no(cls):
        max_member_no = cls.objects.aggregate(models.Max("member_no"))["member_no__max"]
        return (max_member_no or 0) + 1

    def save(self, *args, **kwargs):
        if not self.member_no:
            self.member_no = self.generate_member_no()

        if "bypass_keycloak" not in kwargs:
            kwargs["bypass_keycloak"] = get_parameter_value(
                Parameter.MEMBER_BYPASS_KEYCLOAK
            )

        super().save(*args, **kwargs)

    def is_in_coop_trial(self):
        entry_date = self.coop_entry_date
        return entry_date is not None and entry_date > datetime.date.today()

    def coop_shares_total_value(self):
        today = datetime.date.today()
        return self.coopsharetransaction_set.filter(valid_at__lte=today).aggregate(
            total_value=Sum(F("quantity") * F("share_price"))
        )["total_value"]

    @property
    def coop_shares_quantity(self):
        today = datetime.date.today()
        return self.coopsharetransaction_set.filter(valid_at__lte=today).aggregate(
            quantity=Sum(F("quantity"))
        )["quantity"]

    def monthly_payment(self):
        from tapir.wirgarten.service.products import get_active_subscriptions

        today = datetime.date.today()
        return (
            get_active_subscriptions()
            .filter(member_id=self.id)
            .annotate(
                product_price=Case(
                    When(
                        product__productprice__valid_from__lte=today,
                        then=F("product__productprice__price"),
                    ),
                    default=0.0,
                    output_field=models.FloatField(),
                ),
            )
            .aggregate(
                total_value=Sum(
                    F("product_price") * F("quantity") * (1 + F("solidarity_price"))
                )
            )["total_value"]
        )

    @property
    def coop_entry_date(self):
        try:
            earliest_coopsharetransaction = self.coopsharetransaction_set.filter(
                transaction_type__in=[
                    CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                    CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN,
                ]
            ).earliest("valid_at")
            return (
                earliest_coopsharetransaction.valid_at
                if earliest_coopsharetransaction
                else None
            )
        except CoopShareTransaction.DoesNotExist:
            return None

    def __str__(self):
        return f"[{self.member_no}] {self.first_name} {self.last_name} ({self.email})"


class Product(TapirModel):
    """
    This is a specific product variation, like "Harvest Shares - M".
    """

    type = models.ForeignKey(
        ProductType, on_delete=models.DO_NOTHING, editable=False, null=False
    )
    name = models.CharField(max_length=128, editable=True, null=False)
    deleted = models.BooleanField(default=False)

    class Meta:
        indexes = [Index(fields=["type"], name="idx_product_type")]

    def __str__(self):
        return f"{self.name} ({self.type.name})"


class ProductPrice(TapirModel):
    """
    Price for a product. A product is only valid to use if it has a price.
    """

    product = models.ForeignKey(
        Product, on_delete=models.DO_NOTHING, editable=False, null=False
    )
    price = models.DecimalField(
        decimal_places=2, max_digits=8, editable=False, null=False
    )
    valid_from = models.DateField(null=False, editable=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["product", "valid_from"],
                name="unique_product_price_date",
            )
        ]
        indexes = [Index(fields=["product"], name="idx_productprice_product")]


class HarvestShareProduct(Product):
    """
    Product variations of harvest share products.
    """

    min_coop_shares = models.IntegerField()


class MandateReference(models.Model):
    """
    The mandate reference is generated for the SEPA payments.
    """

    ref = models.CharField(primary_key=True, null=False, blank=False, max_length=35)
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    start_ts = models.DateTimeField(null=False)
    end_ts = models.DateTimeField(null=True)

    class Meta:
        indexes = [Index(fields=["member"], name="idx_mandatereference_mamber")]


class Payable:
    """
    Interface to define how to calculate the total amount.
    """

    def total_price(self):
        raise NotImplementedError(
            "You need to implement total_price() if you use the PayableMixin!"
        )


class Subscription(TapirModel, Payable):
    """
    A subscription for a member.
    """

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, null=False)
    period = models.ForeignKey(GrowingPeriod, on_delete=models.DO_NOTHING, null=False)
    quantity = models.PositiveSmallIntegerField(null=False)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    cancellation_ts = models.DateTimeField(null=True)
    solidarity_price = models.FloatField(default=0.0)
    mandate_ref = models.ForeignKey(
        MandateReference, on_delete=models.DO_NOTHING, null=False
    )
    created_at = models.DateTimeField(default=partial(timezone.now), null=False)
    consent_ts = models.DateTimeField(
        null=True
    )  # TODO this should probably be null=False
    withdrawal_consent_ts = models.DateTimeField(null=True)

    class Meta:
        indexes = [models.Index(fields=["period_id", "created_at"])]

    @property
    def trial_end_date(self):
        return self.start_date + relativedelta(months=1, day=1, days=-1)

    @property
    def total_price(self):
        today = datetime.date.today()
        if not hasattr(self, "_total_price"):
            product_prices = ProductPrice.objects.filter(
                product_id=self.product_id, valid_from__lte=today
            ).order_by("product_id", "-valid_from")
            price = next(
                (
                    product_price.price
                    for product_price in product_prices
                    if product_price.product_id == self.product_id
                ),
                0.0,
            )
            self._total_price = round(
                float(self.quantity) * float(price) * float(1 + self.solidarity_price),
                2,
            )
        return self._total_price

    def __str__(self):
        return f"{self.quantity} × {self.product.name} {self.product.type.name}"


class CoopShareTransaction(TapirModel, Payable):
    """
    The CoopShareTransaction model represents a transaction related to cooperative shares. It provides a way to track various types of transactions that can occur within a cooperative, such as purchasing, canceling, transferring out, and transferring in shares.

    Attributes:
        transaction_type (CharField): The type of transaction (PURCHASE, CANCELLATION, TRANSFER_OUT, TRANSFER_IN).
        member (ForeignKey): The member associated with the transaction.
        quantity (SmallIntegerField): The quantity of shares involved in the transaction. Must be positive for PURCHASE and TRANSFER_IN, and negative for CANCELLATION and TRANSFER_OUT.
        share_price (DecimalField): The price of a single share at the time of the transaction.
        timestamp (DateTimeField): The date and time when the transaction was created.
        valid_at (DateField): The date when the transaction becomes valid.
        mandate_ref (ForeignKey): The reference to a mandate associated with the transaction (optional).
        transfer_member (ForeignKey): The member associated with the share transfer (TRANSFER_OUT, TRANSFER_IN transactions only).
    """

    class CoopShareTransactionType(models.TextChoices):
        PURCHASE = "purchase", _("Zeichnung von Anteilen")
        CANCELLATION = "cancellation", _("Kündigung von Anteilen")
        TRANSFER_OUT = "transfer_out", _("Abgabe von Anteilen")
        TRANSFER_IN = "transfer_in", _("Empfang von Anteilen")

    transaction_type = models.CharField(
        max_length=30, choices=CoopShareTransactionType.choices, null=False
    )
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    quantity = models.SmallIntegerField(null=False)
    share_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    timestamp = models.DateTimeField(default=partial(timezone.now), null=False)
    valid_at = models.DateField(null=False)
    mandate_ref = models.ForeignKey(
        MandateReference, on_delete=models.DO_NOTHING, null=True
    )
    transfer_member = models.ForeignKey(
        Member, on_delete=models.DO_NOTHING, null=True, related_name="transfer_member"
    )

    @property
    def total_price(self):
        return self.quantity * self.share_price

    def clean(self):
        # Call the parent class's clean method to ensure any default validation is performed.
        super().clean()

        # Validate the quantity based on the transaction_type.
        if (
            self.transaction_type
            in [
                self.CoopShareTransactionType.CANCELLATION,
                self.CoopShareTransactionType.TRANSFER_OUT,
            ]
            and self.quantity >= 0
        ):
            raise ValidationError(
                {
                    "quantity": _(
                        "For CANCELLATION and TRANSFER_OUT, the quantity must be negative."
                    )
                }
            )
        elif (
            self.transaction_type
            in [
                self.CoopShareTransactionType.PURCHASE,
                self.CoopShareTransactionType.TRANSFER_IN,
            ]
            and self.quantity <= 0
        ):
            raise ValidationError(
                {
                    "quantity": _(
                        "For PURCHASE and TRANSFER_IN, the quantity must be positive."
                    )
                }
            )

        if (
            self.transaction_type
            in [
                self.CoopShareTransactionType.TRANSFER_IN,
                self.CoopShareTransactionType.TRANSFER_OUT,
            ]
            and self.transfer_member is None
        ):
            raise ValidationError(
                {
                    "transfer_member": _(
                        "For TRASNFER_OUT and TRANSFER_IN, the transfer_member must be set."
                    )
                }
            )

    def save(self, *args, **kwargs):
        # Call the clean method to validate the model instance before saving.
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        prefix = f"[{format_date(self.timestamp)}] {abs(self.quantity)} Genossenschaftsanteile"
        if self.transaction_type == self.CoopShareTransactionType.PURCHASE:
            suffix = "gezeichnet"
        elif self.transaction_type == self.CoopShareTransactionType.CANCELLATION:
            suffix = "gekündigt"
        elif self.transaction_type == self.CoopShareTransactionType.TRANSFER_OUT:
            suffix = f"übertragen an {self.transfer_member}"
        elif self.transaction_type == self.CoopShareTransactionType.TRANSFER_IN:
            suffix = f"empfangen von {self.transfer_member}"
        return f"{prefix} {suffix}"


class ExportedFile(TapirModel):
    """
    An exported file (blob in DB).
    """

    class FileType(models.TextChoices):
        CSV = "csv", _("CSV")
        PDF = "pdf", _("PDF")

    name = models.CharField(max_length=256, null=False)
    type = models.CharField(max_length=8, choices=FileType.choices, null=False)
    file = models.BinaryField(null=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False)


class PaymentTransaction(TapirModel):
    """
    A payment transaction. This is usually created once a month by a task, when the payments are due.
    The relevant payments must reference the transaction in the same step.
    """

    created_at = models.DateTimeField(null=False, default=partial(timezone.now))
    file = models.ForeignKey(ExportedFile, on_delete=models.DO_NOTHING, null=False)


class Payment(TapirModel):
    """
    A payment. Usually payments are created in DB when they are due, but also when the admin edits a future payment.
    If the sepa_payments reference is set, the payment cannot be changed anymore, because it was exported for the bank already.
    """

    class PaymentStatus(models.TextChoices):
        PAID = "PAID", _("Bezahlt")
        DUE = "DUE", _("Offen")

    due_date = models.DateField(null=False)
    mandate_ref = models.ForeignKey(
        MandateReference, on_delete=models.DO_NOTHING, null=False
    )
    amount = models.DecimalField(decimal_places=2, max_digits=8, null=False)
    status = models.CharField(
        max_length=8,
        choices=PaymentStatus.choices,
        null=False,
        default=PaymentStatus.DUE,
    )
    edited = models.BooleanField(default=False, null=False)
    transaction = models.ForeignKey(
        PaymentTransaction, on_delete=models.DO_NOTHING, null=True
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["mandate_ref", "due_date"],
                name="unique_mandate_ref_date",
            )
        ]
        indexes = [Index(fields=["mandate_ref"], name="idx_payment_mandate_ref")]


class Deliveries(TapirModel):
    """
    History of deliveries.
    """

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    delivery_date = models.DateField(null=False)
    pickup_location = models.ForeignKey(
        PickupLocation, on_delete=models.DO_NOTHING, null=False
    )


class TaxRate(TapirModel):
    """
    Tax rates per product type. This has no influence on the gross price, it is only used to calculate the tax amount from the gross price.
    If valid_to == NULL, the tax rate is used as a fallback. If valid_to != NULL and it is now valid, this one is used.
    """

    product_type = models.ForeignKey(
        ProductType, on_delete=models.DO_NOTHING, null=False
    )
    tax_rate = models.FloatField(null=False)
    valid_from = models.DateField(null=False, default=partial(datetime.date.today))
    valid_to = models.DateField(null=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["product_type", "valid_from"],
                name="unique_tax_rate_product_type_valid_from",
            )
        ]
        indexes = [Index(fields=["product_type"], name="idx_tax_rate_product_type")]


class EditFuturePaymentLogEntry(UpdateModelLogEntry):
    """
    This log entry is created whenever an admin manually changes the amount of a future payment.
    """

    template_name = "wirgarten/log/edit_future_payment_log_entry.html"

    comment = models.CharField(null=False, blank=False, max_length=256)

    def populate(
        self,
        old_frozen=None,
        new_frozen=None,
        old_model=None,
        new_model=None,
        comment=None,
        **kwargs,
    ):
        super(EditFuturePaymentLogEntry, self).populate(
            old_frozen=old_frozen,
            new_frozen=new_frozen,
            old_model=old_model,
            new_model=new_model,
        )
        self.comment = comment
        return self


class TransferCoopSharesLogEntry(LogEntry):
    """
    Documents the transfer of coop shares from 'user' to 'target_member'.
    """

    template_name = "wirgarten/log/transfer_coop_shares_log_entry.html"

    target_member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    quantity = models.PositiveSmallIntegerField()

    def populate(
        self, actor=None, user=None, target_member=None, quantity=None, **kwargs
    ):
        super(TransferCoopSharesLogEntry, self).populate(actor=actor, user=user)
        self.target_member = target_member
        self.quantity = quantity
        return self


class ReceivedCoopSharesLogEntry(TransferCoopSharesLogEntry):
    """
    Same as TransferCoopSharesLogEntry, but user and target_member are switched. Then you have a log entry for both sides of the transaction.
    """

    template_name = "wirgarten/log/received_coop_shares_log_entry.html"


class SubscriptionChangeLogEntry(LogEntry):
    """
    This log entry is created whenever a Subscription is created or cancelled.
    """

    template_name = "wirgarten/log/subscription_log_entry.html"

    class SubscriptionChangeLogEntryType(models.TextChoices):
        ADDED = "ADDED", _("Vertragsabschluss")
        CANCELLED = "CANCELLED", _("Kündigung")
        RENEWED = "RENEWED", _("Verlängerung")
        NOT_RENEWED = "NOT_RENEWED", _("Keine Verlängerung")

    change_type = models.CharField(
        choices=SubscriptionChangeLogEntryType.choices, null=False, max_length=32
    )
    subscriptions = models.CharField(null=False, blank=False, max_length=1024)

    def populate(
        self,
        actor: TapirUser,
        user: Member,
        change_type: SubscriptionChangeLogEntryType,
        subscriptions: [Subscription],
        **kwargs,
    ):
        super().populate(actor=actor, user=user, **kwargs)
        self.change_type = change_type
        self.subscriptions = ", ".join(
            list(
                map(
                    lambda x: f"{x} ({format_date(x.start_date)} - {format_date(x.end_date)})",
                    subscriptions,
                )
            )
        )

        return self

    def get_context_data(self):
        context = super().get_context_data()
        context["subscriptions"] = self.subscriptions.split(", ")
        context["change_type"] = self.change_type
        return context


class WaitingListEntry(TapirModel):
    class WaitingListType(models.TextChoices):
        HARVEST_SHARES = "HARVEST_SHARES", _("Ernteanteile")
        COOP_SHARES = "COOP_SHARES", _("Genossenschaftsanteile")

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=True)
    first_name = models.CharField(null=False, blank=False, max_length=256)
    last_name = models.CharField(null=False, blank=False, max_length=256)
    email = models.CharField(null=False, blank=False, max_length=256)
    type = models.CharField(choices=WaitingListType.choices, null=False, max_length=32)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    privacy_consent = models.DateTimeField(null=False)


class QuestionaireTrafficSourceOption(TapirModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class QuestionaireTrafficSourceResponse(TapirModel):
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=True)
    sources = models.ManyToManyField(QuestionaireTrafficSourceOption)

    def __str__(self):
        return self.name
