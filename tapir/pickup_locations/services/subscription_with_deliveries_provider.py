import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.deliveries.services.pick_list_builder import PickListBuilder
from tapir.subscriptions.services.subscription_delivered_in_week_checked import (
    SubscriptionDeliveredInWeekChecker,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import PickupLocation, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_product_price


class SubscriptionsWithDeliveriesProvider:
    @classmethod
    def get_subscriptions_delivered_at_location_and_week(
        cls,
        pickup_location: PickupLocation,
        reference_datetime: datetime.datetime,
        cache: dict,
    ):
        subscriptions = []
        for product_type in TapirCache.get_all_product_types(cache=cache):
            if not DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type, date=reference_datetime.date(), cache=cache
            ):
                continue

            subscriptions.extend(
                PickListBuilder.get_subscriptions_grouped_by_pickup_location_name(
                    delivery_date=reference_datetime.date(),
                    cache=cache,
                    product_type=product_type,
                ).get(pickup_location.name, [])
            )

        subscription_ids = [
            subscription.id
            for subscription in subscriptions
            if SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
                subscription=subscription,
                delivery_date=reference_datetime.date(),
                cache=cache,
                skip_donation_check=get_parameter_value(
                    key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
                    cache=cache,
                )
                == pickup_location.id,
            )
        ]

        subscriptions = Subscription.objects.filter(
            id__in=subscription_ids
        ).select_related("member", "product__type")

        return sorted(
            subscriptions,
            key=lambda subscription: (
                subscription.member.last_name,
                subscription.member.first_name,
                -get_product_price(
                    product=subscription.product_id,
                    reference_date=reference_datetime.date(),
                    cache=cache,
                ).price,
            ),
        )
