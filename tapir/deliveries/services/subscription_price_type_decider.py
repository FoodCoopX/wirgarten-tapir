from tapir.wirgarten.constants import CUSTOM_CYCLE


class SubscriptionPriceTypeDecider:
    @staticmethod
    def is_price_by_delivery(delivery_cycle: str):
        return delivery_cycle == CUSTOM_CYCLE[0]
