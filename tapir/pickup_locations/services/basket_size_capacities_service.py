from django.core.exceptions import ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.models import (
    ProductBasketSizeEquivalence,
    PickupLocationBasketCapacity,
)
from tapir.wirgarten.models import Product, PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys


class BasketSizeCapacitiesService:
    @classmethod
    def validate_basket_sizes(cls, basket_sizes_as_string: str):
        try:
            cls.get_basket_sizes(basket_sizes_as_string)
        except Exception as e:
            raise ValidationError(f"Invalid basket sizes value: {e}")

    @classmethod
    def get_basket_sizes(cls, basket_sizes_as_string: str | None = None):
        if basket_sizes_as_string is None:
            basket_sizes_as_string = get_parameter_value(
                ParameterKeys.PICKING_BASKET_SIZES
            )

        basket_sizes = basket_sizes_as_string.split(";")

        return [size for size in basket_sizes if size.strip() != ""]

    @classmethod
    def get_basket_size_equivalences_for_product(cls, product: Product):
        equivalences = {size_name: 0 for size_name in cls.get_basket_sizes()}
        for equivalence in ProductBasketSizeEquivalence.objects.filter(product=product):
            if equivalence.basket_size_name not in equivalences.keys():
                continue

            equivalences[equivalence.basket_size_name] = equivalence.quantity
        return equivalences

    @classmethod
    def get_basket_size_capacities_for_pickup_location(
        cls, pickup_location: PickupLocation
    ):
        capacities = {size_name: None for size_name in cls.get_basket_sizes()}
        for equivalence in PickupLocationBasketCapacity.objects.filter(
            pickup_location=pickup_location
        ):
            if equivalence.basket_size_name not in capacities.keys():
                continue

            capacities[equivalence.basket_size_name] = equivalence.capacity
        return capacities
