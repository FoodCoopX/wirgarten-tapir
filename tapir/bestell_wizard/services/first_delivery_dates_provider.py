import datetime

from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.pickup_locations.services.pickup_location_active_filter import (
    PickupLocationActiveFilter,
)
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import PickupLocation


class FirstDeliveryDatesProvider:
    @classmethod
    def get_delivery_date_by_pickup_location_id_and_product_type_id(
        cls, order: TapirOrder, contract_start_date: datetime.date, cache: dict
    ) -> dict[str, dict[str, datetime.date]]:
        product_types = [
            TapirCache.get_product_type_by_id(
                cache=cache, product_type_id=product_type_id
            )
            for product_type_id in {product.type_id for product in order.keys()}
        ]
        pickup_location_ids = PickupLocationActiveFilter.get_active_at_date(
            PickupLocation.objects.all(), contract_start_date
        ).values_list("id", flat=True)

        return {
            pickup_location_id: {
                product_type.id: DeliveryDateCalculator.get_next_delivery_date_for_product_type(
                    reference_date=contract_start_date,
                    pickup_location_id=pickup_location_id,
                    product_type=product_type,
                    check_for_weeks_without_delivery=True,
                    cache=cache,
                )
                for product_type in product_types
            }
            for pickup_location_id in pickup_location_ids
        }
