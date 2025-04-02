from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class BaseProductTypeService:
    VALUE_NO_BASE_PRODUCT_TYPE = "no_base_product_type"

    @classmethod
    def get_base_product_type(cls):
        from tapir.wirgarten.models import ProductType

        base_product_type_id = get_parameter_value(ParameterKeys.COOP_BASE_PRODUCT_TYPE)
        if base_product_type_id == cls.VALUE_NO_BASE_PRODUCT_TYPE:
            return None

        base_product_type = ProductType.objects.filter(id=base_product_type_id).first()
        if base_product_type is None:
            raise ImproperlyConfigured(
                f"The base product ID is set to'{base_product_type_id}', but no product with that ID was found.'"
            )

        return base_product_type

    @classmethod
    def get_options_for_base_product_type_parameter(cls):
        from tapir.wirgarten.models import ProductType

        product_type_id_to_product_type_name = map(
            lambda x: (x.id, x.name), ProductType.objects.all()
        )
        return [(cls.VALUE_NO_BASE_PRODUCT_TYPE, "Kein Basis Produkttyp")] + list(
            product_type_id_to_product_type_name
        )
