from django.db import models
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _
from localflavor.generic.models import IBANField, BICField

from tapir.accounts.models import TapirUser
from tapir.core.models import TapirModel


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

    name = models.CharField(max_length=128, null=False)
    pickup_enabled = models.BooleanField(null=False, default=False)


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


class Payment(TapirModel):
    """
    A payment. Usually payments are created in DB when they are due.
    """

    class PaymentStatus(models.TextChoices):
        UPCOMING = "UPCOMING", _("Bevorstehend")
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
