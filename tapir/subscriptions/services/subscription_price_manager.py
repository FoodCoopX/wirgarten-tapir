from datetime import datetime

from tapir.subscriptions.services.solidarity_validator import SolidarityValidator
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.utils import get_today


class SubscriptionPriceManager:
    @staticmethod
    def get_monthly_price_of_order_without_solidarity(
        order: TapirOrder,
        reference_date: datetime.date,
        cache: dict = None,
    ):
        total = 0.0
        for product, quantity in order.items():
            product_price_object = get_product_price(
                product=product, reference_date=reference_date, cache=cache
            )
            total += float(product_price_object.price) * quantity
        return total

    @classmethod
    def get_monthly_price_of_subscription_without_solidarity(
        cls,
        subscription: Subscription,
        reference_date: datetime.date = None,
        cache: dict = None,
    ):
        if subscription.price_override is not None:
            return float(subscription.price_override)

        if reference_date is None:
            reference_date = max(subscription.start_date, get_today(cache=cache))

        subscription_price_without_solidarity = (
            cls.get_monthly_price_of_order_without_solidarity(
                order={subscription.product: subscription.quantity},
                reference_date=reference_date,
                cache=cache,
            )
        )

        return round(
            subscription_price_without_solidarity
            + SolidarityValidator.get_solidarity_factor_of_subscription(
                subscription=subscription, reference_date=reference_date, cache=cache
            ),
            2,
        )
