import datetime

from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.pickup_locations.services.public_pickup_locations_provider import (
    PublicPickupLocationProvider,
)
from tapir.subscriptions.types import TapirOrder


class PickupLocationsWithEnoughCapacityProvider:
    @classmethod
    def get_pickup_location_ids(
        cls, order: TapirOrder, subscription_start: datetime.date, cache: dict
    ) -> list[str]:
        candidates = (
            PublicPickupLocationProvider.get_pickup_locations_available_for_members(
                cache=cache, reference_date=subscription_start
            )
        )

        return [
            pickup_location.id
            for pickup_location in candidates
            if PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                pickup_location=pickup_location,
                order=order,
                already_registered_member=None,
                subscription_start=subscription_start,
                cache=cache,
            )
        ]
