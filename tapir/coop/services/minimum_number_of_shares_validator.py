from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.parameter_keys import ParameterKeys


class MinimumNumberOfSharesValidator:
    @staticmethod
    def get_minimum_number_of_shares_for_order(
        ordered_products_id_to_quantity_map: dict, cache: dict
    ):
        min_number_of_shares_from_order = sum(
            [
                TapirCache.get_product_by_id(
                    cache=cache, product_id=product_id
                ).min_coop_shares
                * quantity
                for product_id, quantity in ordered_products_id_to_quantity_map.items()
            ]
        )

        min_number_of_shares_from_config = get_parameter_value(
            ParameterKeys.COOP_MIN_SHARES, cache=cache
        )

        return max(min_number_of_shares_from_config, min_number_of_shares_from_order)

    @classmethod
    def get_minimum_number_of_shares_for_tapir_order(
        cls, order: TapirOrder, cache: dict
    ):
        transformed_order = {
            product.id: quantity for product, quantity in order.items()
        }
        return cls.get_minimum_number_of_shares_for_order(
            ordered_products_id_to_quantity_map=transformed_order, cache=cache
        )
