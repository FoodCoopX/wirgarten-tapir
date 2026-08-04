import datetime
from decimal import Decimal

from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.pickup_locations.config import PICKING_MODE_BASKET, PICKING_MODE_SHARE
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.pickup_locations.services.picking_mode_provider import PickingModeProvider
from tapir.pickup_locations.services.subscription_with_deliveries_provider import (
    SubscriptionsWithDeliveriesProvider,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import PickupLocation, Subscription, Product
from tapir.wirgarten.service.products import get_product_price


class PickupLocationDataForLocationRouteBuilder:
    @classmethod
    def build_data_for_location_route(
        cls,
        pickup_location: PickupLocation,
        reference_datetime: datetime.datetime,
        cache: dict,
    ):
        subscriptions = SubscriptionsWithDeliveriesProvider.get_subscriptions_delivered_at_location_and_week(
            pickup_location=pickup_location,
            reference_datetime=reference_datetime,
            cache=cache,
        )

        global_values = cls.get_table_values(
            subscriptions=subscriptions,
            cache=cache,
            reference_date=reference_datetime.date(),
        )
        members = {subscription.member for subscription in subscriptions}
        members = sorted(
            members,
            key=lambda member: (
                member.member_no,
                member.last_name,
                member.first_name,
            ),
        )
        members_values = {
            member: cls.get_table_values(
                subscriptions=[
                    subscription
                    for subscription in subscriptions
                    if subscription.member_id == member.id
                ],
                cache=cache,
                reference_date=reference_datetime.date(),
            )
            for member in members
        }

        return {
            "id": pickup_location.id,
            "name": pickup_location.name,
            "street": pickup_location.street,
            "street_2": pickup_location.street_2,
            "postcode": pickup_location.postcode,
            "city": pickup_location.city,
            "route_info": pickup_location.route_info,
            "headers": cls.get_headers(
                cache=cache, reference_date=reference_datetime.date()
            ),
            "product_name_by_id": {
                product.id: product.name
                for product in TapirCache.get_all_products(cache=cache)
            },
            "convert_headers": PickingModeProvider.get_picking_mode(cache=cache)
            == PICKING_MODE_SHARE,
            "global_values": global_values,
            "members": [
                {
                    "member_no": member.member_no,
                    "last_name": member.last_name[:2],
                    "first_name": member.first_name,
                    "member_values": members_values[member],
                }
                for member in members
            ],
            "calendar_week": reference_datetime.isocalendar().week,
        }

    @classmethod
    def get_table_values(
        cls,
        subscriptions: list[Subscription],
        cache: dict,
        reference_date: datetime.date,
    ):
        picking_mode = PickingModeProvider.get_picking_mode(cache=cache)
        values = dict.fromkeys(
            cls.get_headers(cache=cache, reference_date=reference_date), 0
        )
        if picking_mode == PICKING_MODE_BASKET:
            for subscription in subscriptions:
                equivalences = BasketSizeCapacitiesService.get_basket_size_equivalences_for_product(
                    product=subscription.product, cache=cache
                )
                for basket_name, quantity in equivalences.items():
                    values[basket_name] += quantity
        elif picking_mode == PICKING_MODE_SHARE:
            for subscription in subscriptions:
                values[subscription.product_id] += subscription.quantity

        return values

    @classmethod
    def get_headers(cls, cache: dict, reference_date: datetime.date):
        picking_mode = PickingModeProvider.get_picking_mode(cache=cache)
        if picking_mode == PICKING_MODE_BASKET:
            return BasketSizeCapacitiesService.get_basket_sizes(cache=cache)

        products = [
            product
            for product in TapirCache.get_all_products(cache=cache)
            if DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product.type, date=reference_date, cache=cache
            )
        ]
        products = sorted(
            products,
            key=lambda product: (
                product.type.order_in_bestellwizard,
                cls.get_price_or_zero(
                    product=product, reference_date=reference_date, cache=cache
                ),
            ),
        )
        return [product.id for product in products]

    @classmethod
    def get_price_or_zero(
        cls, product: Product, reference_date: datetime.date, cache: dict
    ):
        price_object = get_product_price(
            product=product, reference_date=reference_date, cache=cache
        )
        return Decimal(0) if price_object is None else price_object.price
