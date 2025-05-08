from typing import Dict

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class WaitingListCategoriesService:
    @classmethod
    def get_categories(cls, cache: Dict):
        base_string = get_parameter_value(
            ParameterKeys.SUBSCRIPTION_WAITING_LIST_CATEGORIES, cache=cache
        )
        base_string = base_string.strip()
        if base_string == "":
            return []
        categories = base_string.split(",")
        categories = [category.strip() for category in categories]
        return categories
