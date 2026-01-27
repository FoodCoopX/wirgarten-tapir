from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys


class PublicPickupLocationProvider:
    @classmethod
    def get_pickup_locations_available_for_members(cls, cache: dict):
        return PickupLocation.objects.order_by("name").exclude(
            id=get_parameter_value(
                key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
                cache=cache,
            )
        )
