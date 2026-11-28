import datetime

from tapir.subscriptions.services.global_capacity_checker import (
    GlobalCapacityChecker,
)
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.subscriptions.types import TapirOrder


class ProductsOverCapacityForOrderProvider:
    @classmethod
    def get_product_type_ids(
        cls, order: TapirOrder, contract_start_date: datetime.date, cache: dict
    ) -> list[str]:
        return GlobalCapacityChecker.get_product_type_ids_without_enough_capacity_for_order(
            order_with_all_product_types=order,
            member_id=None,
            subscription_start_date=contract_start_date,
            cache=cache,
        )

    @classmethod
    def get_product_ids(
        cls, order: TapirOrder, contract_start_date: datetime.date, cache: dict
    ) -> list[str]:
        return [
            product.id
            for product, quantity in order.items()
            if not ProductCapacityChecker.does_product_have_enough_free_capacity_to_add_order(
                product=product,
                ordered_quantity=quantity,
                member_id=None,
                subscription_start_date=contract_start_date,
                cache=cache,
            )
        ]
