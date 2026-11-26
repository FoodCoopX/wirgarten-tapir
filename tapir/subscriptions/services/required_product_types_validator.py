from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache


class RequiredProductTypesValidator:
    @classmethod
    def does_order_contain_all_required_product_types(
        cls, order: TapirOrder, cache: dict
    ):
        if len(order) == 0:
            return True

        required_product_type_ids = {
            product_type.id
            for product_type in TapirCache.get_all_product_types(cache=cache)
            if product_type.must_be_subscribed_to
        }
        ordered_product_type_ids = {product.type_id for product in order.keys()}
        return required_product_type_ids.issubset(ordered_product_type_ids)
