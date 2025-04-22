from typing import Dict

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.parameter_keys import ParameterKeys


class BaseProductTypeService:
    @classmethod
    def get_base_product_type(cls, cache: Dict):
        from tapir.wirgarten.models import ProductType

        base_product_type_id = get_parameter_value(
            ParameterKeys.COOP_BASE_PRODUCT_TYPE, cache
        )

        def compute():
            base_product_type = ProductType.objects.filter(
                id=base_product_type_id
            ).first()
            if base_product_type is None:
                raise ImproperlyConfigured(
                    f"The base product ID is set to'{base_product_type_id}', but no product with that ID was found.'"
                )
            return base_product_type

        return get_from_cache_or_compute(cache, "base_product_type", compute)
