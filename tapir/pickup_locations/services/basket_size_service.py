from django.core.exceptions import ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameters import Parameter


class BasketSizeService:
    @classmethod
    def validate_basket_sizes(cls, basket_sizes_as_string: str):
        try:
            cls.get_basket_sizes(basket_sizes_as_string)
        except Exception as e:
            raise ValidationError(f"Invalid basket sizes value: {e}")

    @classmethod
    def get_basket_sizes(cls, basket_sizes_as_string: str | None = None):
        if basket_sizes_as_string is None:
            basket_sizes_as_string = get_parameter_value(Parameter.PICKING_BASKET_SIZES)

        basket_sizes = ";".split(basket_sizes_as_string)

        return [size for size in basket_sizes if size.strip() != ""]
