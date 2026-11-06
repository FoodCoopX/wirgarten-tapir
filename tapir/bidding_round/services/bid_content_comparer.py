from collections import Counter


class BidContentComparer:
    @classmethod
    def items_are_equal(cls, previous_items, proposed_items) -> bool:
        return cls._item_values(previous_items) == cls._item_values(proposed_items)

    @staticmethod
    def _item_values(items):
        return Counter(
            (
                str(item.round_product_id),
                str(item.product_id),
                item.quantity,
                item.amount_1,
                item.amount_2,
                item.amount_3,
            )
            for item in items
        )
