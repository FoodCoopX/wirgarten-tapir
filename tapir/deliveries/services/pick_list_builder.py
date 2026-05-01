import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.config import DELIVERY_DONATION_DONT_FORWARD_TO_PICKUP_LOCATION
from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.subscription_delivered_in_week_checked import (
    SubscriptionDeliveredInWeekChecker,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    ProductType,
    Product,
    ProductPrice,
    Subscription,
    Member,
    PickupLocation,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.file_export import begin_csv_string
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_product_price,
)


class PickListBuilder:
    KEY_PICKUP_LOCATION = "Abholort"
    KEY_M_EQUIVALENT = "M-Äquivalent"

    @classmethod
    def build_pick_list(
        cls, product_type: ProductType, delivery_date: datetime.date, cache: dict
    ):
        subscriptions_by_pickup_location_name = (
            cls.get_subscriptions_grouped_by_pickup_location_name(
                delivery_date=delivery_date, cache=cache, product_type=product_type
            )
        )
        products = cls.get_relevant_products(
            product_type=product_type, delivery_date=delivery_date, cache=cache
        )

        header = [
            cls.KEY_PICKUP_LOCATION,
            *[product.name for product in products],
            cls.KEY_M_EQUIVALENT,
        ]

        output, writer = begin_csv_string(header)

        sorted_pickup_location_names = sorted(
            subscriptions_by_pickup_location_name.keys()
        )
        for pickup_location_name in sorted_pickup_location_names:
            data = cls.build_row_data_for_pickup_location(
                subscriptions_by_pickup_location_name=subscriptions_by_pickup_location_name,
                pickup_location_name=pickup_location_name,
                delivery_date=delivery_date,
                cache=cache,
            )
            writer.writerow(data)

        return "".join(output.csv_string)

    @classmethod
    def build_row_data_for_pickup_location(
        cls,
        subscriptions_by_pickup_location_name: dict[str, list[Subscription]],
        pickup_location_name: str,
        delivery_date: datetime.date,
        cache: dict,
    ):
        subscriptions = cls.get_delivered_subscriptions(
            subscriptions=subscriptions_by_pickup_location_name[pickup_location_name],
            delivery_date=delivery_date,
            cache=cache,
        )
        subscriptions.sort(key=lambda x: x.product.name)
        quantities_by_product_name = cls.get_delivery_quantity_by_product_name(
            subscriptions
        )

        return {
            cls.KEY_PICKUP_LOCATION: pickup_location_name,
            **quantities_by_product_name,
            cls.KEY_M_EQUIVALENT: cls.get_m_equivalent_size(
                subscriptions=subscriptions,
                delivery_date=delivery_date,
                cache=cache,
            ),
        }

    @classmethod
    def get_m_equivalent_size(
        cls,
        subscriptions: list[Subscription],
        delivery_date: datetime.date,
        cache: dict,
    ):
        return sum(
            [
                get_product_price(
                    product=subscription.product,
                    cache=cache,
                    reference_date=delivery_date,
                ).size
                for subscription in subscriptions
            ]
        )

    @classmethod
    def get_delivery_quantity_by_product_name(cls, subscriptions: list[Subscription]):
        quantities_by_product_name = {}

        for subscription in subscriptions:
            if subscription.product.name not in quantities_by_product_name:
                quantities_by_product_name[subscription.product.name] = 0
            quantities_by_product_name[
                subscription.product.name
            ] += subscription.quantity

        return quantities_by_product_name

    @classmethod
    def get_delivered_subscriptions(
        cls,
        subscriptions: list[Subscription],
        delivery_date: datetime.date,
        cache: dict,
    ):
        return [
            subscription
            for subscription in subscriptions
            if SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
                subscription=subscription,
                delivery_date=delivery_date,
                cache=cache,
                skip_donation_check=True,
            )
        ]

    @classmethod
    def get_relevant_products(
        cls, product_type: ProductType, delivery_date: datetime.date, cache: dict
    ):
        products_ids_with_price = list(
            ProductPrice.objects.filter(valid_from__lte=delivery_date).values_list(
                "product_id", flat=True
            )
        )
        products = Product.objects.filter(
            type_id=product_type.id, id__in=products_ids_with_price
        ).distinct()

        products = list(products)
        products.sort(key=lambda product: get_product_price(product, cache=cache).price)
        return products

    @classmethod
    def get_subscriptions_grouped_by_pickup_location_name(
        cls, delivery_date: datetime.date, cache: dict, product_type: ProductType
    ):
        subscriptions = (
            get_active_subscriptions(delivery_date, cache=cache)
            .filter(product__type_id=product_type.id)
            .select_related("member", "product__type")
            .distinct()
        )
        subscriptions_by_pickup_location_name = {}

        for subscription in subscriptions:
            pickup_location = cls.get_member_pickup_location_for_pick_list(
                member=subscription.member,
                reference_date=delivery_date,
                cache=cache,
                product_type_is_affected_by_jokers=product_type.is_affected_by_jokers,
            )
            if pickup_location is None:
                continue

            if pickup_location.name not in subscriptions_by_pickup_location_name:
                subscriptions_by_pickup_location_name[pickup_location.name] = []

            subscriptions_by_pickup_location_name[pickup_location.name].append(
                subscription
            )

        return subscriptions_by_pickup_location_name

    @classmethod
    def get_member_pickup_location_for_pick_list(
        cls,
        member: Member,
        reference_date: datetime.date,
        cache: dict,
        product_type_is_affected_by_jokers: bool,
    ) -> PickupLocation | None:
        if (
            DeliveryDonationManager.does_member_have_a_donation_in_week(
                member=member, reference_date=reference_date, cache=cache
            )
            and product_type_is_affected_by_jokers
        ):
            pickup_location_id = get_parameter_value(
                key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
                cache=cache,
            )
            if pickup_location_id == DELIVERY_DONATION_DONT_FORWARD_TO_PICKUP_LOCATION:
                return None
        else:
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=member.id, reference_date=reference_date, cache=cache
                )
            )
        if pickup_location_id is None:
            return None

        pickup_location = TapirCache.get_pickup_location_by_id(
            cache=cache, pickup_location_id=pickup_location_id
        )
        return pickup_location
