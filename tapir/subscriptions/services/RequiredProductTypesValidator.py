from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import ProductType


class RequiredProductTypesValidator:
    @classmethod
    def does_order_contain_all_required_product_types(cls, order: TapirOrder):
        required_product_type_ids = set(
            ProductType.objects.filter(must_be_subscribed_to=True).values_list(
                "id", flat=True
            )
        )
        ordered_product_type_ids = {product.type_id for product in order.keys()}
        return required_product_type_ids.issubset(ordered_product_type_ids)
