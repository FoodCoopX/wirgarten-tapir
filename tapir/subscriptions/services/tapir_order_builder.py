from django.http import Http404

from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import WaitingListEntry


class TapirOrderBuilder:
    @classmethod
    def build_tapir_order_from_shopping_cart_serializer(
        cls, shopping_cart: dict, cache: dict
    ) -> TapirOrder:
        for product_id in shopping_cart.keys():
            if TapirCache.get_product_by_id(cache=cache, product_id=product_id) is None:
                raise Http404(f"Unknown product, id: '{product_id}'")

        order: TapirOrder = {
            TapirCache.get_product_by_id(cache=cache, product_id=product_id): quantity
            for product_id, quantity in shopping_cart.items()
            if quantity > 0
        }

        return order

    @classmethod
    def build_tapir_order_from_waiting_list_entry(
        cls, waiting_list_entry: WaitingListEntry
    ) -> TapirOrder:
        wishes = waiting_list_entry.product_wishes.all().select_related("product__type")
        return {wish.product: wish.quantity for wish in wishes}
