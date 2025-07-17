from django.db import models

from tapir.accounts.models import TapirUser
from tapir.core.models import TapirModel
from tapir.log.models import LogEntry
from tapir.wirgarten.models import Product, PickupLocation, MemberPickupLocation


class ProductBasketSizeEquivalence(TapirModel):
    basket_size_name = models.CharField(max_length=128)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"Basket:{self.basket_size_name}, product:{self.product}, quantity:{self.quantity}"


class PickupLocationBasketCapacity(TapirModel):
    basket_size_name = models.CharField(max_length=128)
    pickup_location = models.ForeignKey(PickupLocation, on_delete=models.CASCADE)
    capacity = models.PositiveIntegerField(null=True)


class PickupLocationChangedLogEntry(LogEntry):
    """
    This log entry is created whenever a member changes their pickup location
    """

    template_name = "pickup_locations/log/pickup_location_changed_log_entry.html"
    new_pickup_location_name = models.CharField(max_length=150)
    old_pickup_location_name = models.CharField(max_length=150)
    valid_from = models.DateField()

    def populate_pickup_location(
        self,
        actor: TapirUser | None,
        user: TapirUser | None,
        member_pickup_location: MemberPickupLocation,
        old_pickup_location: PickupLocation,
    ):
        super().populate(actor, user)
        self.new_pickup_location_name = member_pickup_location.pickup_location.name
        self.old_pickup_location_name = old_pickup_location.name
        self.valid_from = member_pickup_location.valid_from

        return self

    def get_context_data(self):
        context_data = super().get_context_data()
        context_data["old_pickup_location_name"] = self.old_pickup_location_name
        context_data["new_pickup_location_name"] = self.new_pickup_location_name
        context_data["valid_from"] = self.valid_from
        return context_data
