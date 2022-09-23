from django.db import models
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _
from localflavor.generic.models import IBANField, BICField

from tapir.accounts.models import TapirUser


class PickupLocation(models.Model):
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


class GrowingPeriod(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()


class ProductType(models.Model):
    name = models.CharField(max_length=128, null=False)


class ProductCapacity(models.Model):
    period = models.ForeignKey(GrowingPeriod, null=False, on_delete=models.DO_NOTHING)
    product_type = models.ForeignKey(
        ProductType, null=False, on_delete=models.DO_NOTHING
    )
    capacity = models.DecimalField(decimal_places=2, max_digits=20, null=False)


class Member(TapirUser, models.Model):
    account_owner = models.CharField(_("Account owner"), max_length=150)
    iban = IBANField(_("IBAN"))
    bic = BICField(_("BIC"))
    sepa_consent = models.DateTimeField(_("SEPA Consent"))
    pickup_location = models.ForeignKey(PickupLocation, on_delete=models.DO_NOTHING)
    withdrawal_consent = models.DateTimeField(_("Right of withdrawal consent"))
    privacy_consent = models.DateTimeField(_("Privacy consent"))


class Product(models.Model):
    type = models.ForeignKey(
        ProductType, on_delete=models.DO_NOTHING, editable=False, null=False
    )
    name = models.CharField(max_length=128, editable=True, null=False)
    price = models.DecimalField(
        decimal_places=2, max_digits=6, editable=False, null=False
    )
    deleted = models.IntegerField(default=0)


class HarvestShareProduct(Product):
    min_coop_shares = models.IntegerField()


class Subscription(models.Model):
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, null=False)
    period = models.ForeignKey(GrowingPeriod, on_delete=models.DO_NOTHING, null=False)
    quantity = models.PositiveSmallIntegerField(null=False)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    cancellation_ts = models.DateTimeField(null=True)
    solidarity_price = models.FloatField(default=0.0)


class ShareOwnership(models.Model):
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    quantity = models.PositiveSmallIntegerField(null=False)
    share_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    entry_date = models.DateField(null=False)
