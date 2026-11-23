import datetime

from tapir.subscriptions.services.global_capacity_checker import (
    GlobalCapacityChecker,
)
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.utils.services.tapir_cache import TapirCache


class ProductsWithoutFreeCapacityProvider:
    @classmethod
    def get_product_type_ids(
        cls,
        cache: dict,
        product_ids_without_free_capacity: list[str],
        contract_start_date: datetime.date,
    ) -> list[str]:
        ids = []

        for product_type in TapirCache.get_product_types_in_standard_order(cache=cache):
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
        cls, cache: dict, contract_start_date: datetime.date
    ) -> list[str]:
        ids = []

        for product in TapirCache.get_all_products(cache=cache):
            if not ProductCapacityChecker.does_product_have_enough_free_capacity_to_add_order(
                product=product,
                ordered_quantity=1,
                member_id=None,
                subscription_start_date=contract_start_date,
                cache=cache,
            ):
                ids.append(product.id)

        return ids
