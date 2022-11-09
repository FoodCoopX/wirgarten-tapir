import datetime
from functools import partial

from django.db import models
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _
from localflavor.generic.models import IBANField, BICField

from tapir.accounts.models import TapirUser
from tapir.core.models import TapirModel
from tapir.log.models import UpdateModelLogEntry
from tapir.wirgarten.constants import DeliveryCycle, NO_DELIVERY


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


class GrowingPeriod(TapirModel):
    """
    The growing period for the WirGarten site. Usually the growing period starts on 1st of March, and ends in the end of next February.
    """

    start_date = models.DateField()
    end_date = models.DateField()


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


class Member(TapirUser):
    """
    A member of WirGarten. Usually a member has coop shares and optionally other subscriptions.
    """

    account_owner = models.CharField(_("Account owner"), max_length=150)
    iban = IBANField(_("IBAN"))
    bic = BICField(_("BIC"))
    sepa_consent = models.DateTimeField(_("SEPA Consent"))
    pickup_location = models.ForeignKey(
        PickupLocation, on_delete=models.DO_NOTHING, null=True
    )
    withdrawal_consent = models.DateTimeField(_("Right of withdrawal consent"))
    privacy_consent = models.DateTimeField(_("Privacy consent"))


class Product(TapirModel):
    """
    This is a specific product variation, like "Harvest Shares - M".
    """

    type = models.ForeignKey(
        ProductType, on_delete=models.DO_NOTHING, editable=False, null=False
    )
    name = models.CharField(max_length=128, editable=True, null=False)
    price = models.DecimalField(
        decimal_places=2, max_digits=6, editable=False, null=False
    )
    deleted = models.IntegerField(default=0)


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


class Subscription(TapirModel):
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


class ShareOwnership(TapirModel):
    """
    Tracks the number of coop shares of a member.
    """

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    quantity = models.PositiveSmallIntegerField(null=False)
    share_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    entry_date = models.DateField(null=False)
    mandate_ref = models.ForeignKey(
        MandateReference, on_delete=models.DO_NOTHING, null=False
    )


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

    created_at = models.DateTimeField(
        null=False, default=partial(datetime.datetime.now)
    )
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


class Deliveries(TapirModel):
    """
    History of deliveries. Usually gets
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


class EditFuturePaymentLogEntry(UpdateModelLogEntry):
    """
    This log entry is created whenever an admin manually changes the amount of a future payment.
    """

    comment = models.CharField(null=False, blank=False, max_length=256)

    def populate(
        self,
        old_frozen=None,
        new_frozen=None,
        old_model=None,
        new_model=None,
        comment=None,
        **kwargs
    ):
        super(EditFuturePaymentLogEntry, self).populate(
            old_frozen=old_frozen,
            new_frozen=new_frozen,
            old_model=old_model,
            new_model=new_model,
        )
        self.comment = comment
        return self
