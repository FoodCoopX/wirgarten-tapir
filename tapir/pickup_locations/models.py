from django.db import models

from tapir.core.models import TapirModel
from tapir.wirgarten.models import Product, PickupLocation


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
