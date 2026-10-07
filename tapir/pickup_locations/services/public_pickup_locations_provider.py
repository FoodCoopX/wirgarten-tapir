import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.pickup_location_active_filter import (
    PickupLocationActiveFilter,
)
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class PublicPickupLocationProvider:
    @classmethod
    def get_pickup_locations_available_for_members(
        cls,
        cache: dict,
        reference_date: datetime.date | None = None,
    ):
        pickup_locations = PickupLocation.objects.order_by("name").exclude(
            id=get_parameter_value(
                key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
                cache=cache,
            )
        )
        return PickupLocationActiveFilter.get_active_at_date(
            pickup_locations,
            reference_date if reference_date is not None else get_today(cache=cache),
        )
