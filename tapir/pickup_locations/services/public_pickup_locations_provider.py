import datetime

from django.db.models import Q

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.pickup_location_active_filter import (
    PickupLocationActiveFilter,
)
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys


class PublicPickupLocationProvider:
    @classmethod
    def get_pickup_locations_available_for_members(
        cls,
        cache: dict,
        reference_date: datetime.date,
        include_future: bool = False,
    ):
        qs = PickupLocation.objects.order_by("name").exclude(
            id=get_parameter_value(
                key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
                cache=cache,
            )
        )
        if include_future:
            return qs.filter(Q(end_date__isnull=True) | Q(end_date__gte=reference_date))
        return PickupLocationActiveFilter.get_active_at_date(qs, reference_date)
