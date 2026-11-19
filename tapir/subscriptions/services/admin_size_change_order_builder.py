import datetime

from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, Product, Subscription


class AdminSizeChangeOrderBuilder:
    @classmethod
    def build_order(
        cls,
        member: Member,
        subscription: Subscription,
        new_product: Product,
        change_date: datetime.date,
        cache: dict,
    ) -> TapirOrder:
        base_date = min(change_date, subscription.end_date)
        order = {}
        for other_subscription in TapirCache.get_all_subscriptions_for_member(
            member_id=member.id, cache=cache
        ):
            if (
                other_subscription.product.type_id != subscription.product.type_id
                or not other_subscription.start_date
                <= base_date
                <= other_subscription.end_date
            ):
                continue
            order[other_subscription.product] = (
                order.get(other_subscription.product, 0) + other_subscription.quantity
            )

        order[subscription.product] = order.get(subscription.product, 0) - 1
        if order[subscription.product] <= 0:
            del order[subscription.product]
        order[new_product] = order.get(new_product, 0) + 1

        return order
