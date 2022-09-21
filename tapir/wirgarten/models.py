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


class Member(TapirUser, models.Model):
    solidarity_price = models.DecimalField(
        _("Solidarpreis"), decimal_places=2, max_digits=3
    )
    account_owner = models.CharField(_("Account owner"), max_length=150)
    iban = IBANField(_("IBAN"))
    bic = BICField(_("BIC"))
    sepa_consent = models.DateTimeField(_("SEPA Consent"))
    pickup_location = models.ForeignKey(PickupLocation, on_delete=models.DO_NOTHING)
    withdrawal_consent = models.DateTimeField(_("Right of withdrawal consent"))
    privacy_consent = models.DateTimeField(_("Privacy consent"))


class ProductBase(models.Model):
    variation = models.CharField(max_length=16, null=True)
    price = models.FloatField()

    # Valid timespan?
    # start_date = models.DateField()
    # end_date = models.DateField()

    class Meta:
        abstract = True


class ChickenShareProduct(ProductBase):
    pass


class HarvestShareProduct(ProductBase):
    min_coop_shares = models.IntegerField()

    # TODO: unique constraints?


class ActiveProduct(models.Model):
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=60)
    variant = models.CharField(max_length=16)
    amount = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
