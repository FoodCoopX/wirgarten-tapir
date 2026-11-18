from tapir.wirgarten.models import Subscription


class SubscriptionCalculationNameBuilder:
    @classmethod
    def build_name(cls, subscription: Subscription) -> str:
        name = f"{subscription.product.type.name} {subscription.product.name}"
        if subscription.price_override is not None:
            return f"{name} (Sonderpreis)"
        if subscription.quantity != 1:
            return f"{name} ({subscription.quantity} Anteile)"
        return name
