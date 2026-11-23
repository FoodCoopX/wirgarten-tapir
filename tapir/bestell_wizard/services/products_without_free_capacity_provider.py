import datetime

from tapir.subscriptions.services.global_capacity_checker import (
    GlobalCapacityChecker,
)
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import ProductType


class ProductsWithoutFreeCapacityProvider:
    @classmethod
    def get_product_type_ids(
        cls,
        product_types: list[ProductType],
        product_ids_without_free_capacity: list[str],
        contract_start_date: datetime.date,
        cache: dict,
    ) -> list[str]:
        ids = []

        for product_type in product_types:
            products = TapirCache.get_products_with_product_type(
                cache=cache, product_type_id=product_type.id
            )
            if len(products) == 0:
                continue

            smallest_product = GlobalCapacityChecker.get_smallest_product(
                product_type=product_type,
                cache=cache,
                reference_date=contract_start_date,
            )

            if not GlobalCapacityChecker.is_there_enough_free_global_capacity_for_single_product_type(
                order_for_a_single_product_type={smallest_product: 1},
                product_type_id=product_type.id,
                cache=cache,
                member_id=None,
                check_waiting_list_entries=True,
                subscription_start_date=contract_start_date,
            ):
                ids.append(product_type.id)
                continue

            no_product_with_free_capacity = all(
                product.id in product_ids_without_free_capacity for product in products
            )

            if no_product_with_free_capacity:
                ids.append(product_type.id)

        return ids

    @classmethod
    def get_product_ids(
        cls,
        product_types: list[ProductType],
        contract_start_date: datetime.date,
        cache: dict,
    ) -> list[str]:
        return [
            product.id
            for product_type in product_types
            for product in TapirCache.get_products_with_product_type(
                cache=cache, product_type_id=product_type.id
            )
            if not ProductCapacityChecker.does_product_have_enough_free_capacity_to_add_order(
                product=product,
                ordered_quantity=1,
                member_id=None,
                subscription_start_date=contract_start_date,
                cache=cache,
            )
        ]
