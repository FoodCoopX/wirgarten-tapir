import datetime

from tapir.deliveries.services.pickup_location_delivery_date_calculator import (
    PickupLocationDeliveryDateCalculator,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.utils.shortcuts import get_monday


class MemberSpecificDeliveryDayCalculator:
    @classmethod
    def get_specific_delivery_date(
        cls, member_id: str, delivery_date: datetime.date, cache: dict
    ):
        return PickupLocationDeliveryDateCalculator.get_delivery_date_at_pickup_location(
            pickup_location_id=MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=member_id,
                reference_date=get_monday(delivery_date),
                cache=cache,
            ),
            delivery_date=delivery_date,
            cache=cache,
        )
