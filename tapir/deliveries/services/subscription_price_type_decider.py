from tapir.wirgarten.constants import CUSTOM_CYCLE


class SubscriptionPricingStrategyDecider:
    @staticmethod
    def is_price_by_delivery(delivery_cycle: str):
        # if not by delivery, then per month
        return delivery_cycle == CUSTOM_CYCLE[0]
