import datetime
from typing import Dict

from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
)


class PickupLocationCapacityGeneralChecker:
    @classmethod
    def does_pickup_location_have_enough_capacity_to_add_subscriptions(
        cls,
        pickup_location: PickupLocation,
        order: TapirOrder,
        already_registered_member: Member | None,
        subscription_start: datetime.date,
        cache: Dict,
    ) -> bool:
        if (
            already_registered_member
            and MemberPickupLocationService.get_member_pickup_location_id(
                already_registered_member, subscription_start
            )
            != pickup_location.id
        ):
            already_registered_member = None

        return PickupLocationCapacityModeShareChecker.check_for_picking_mode_share(
            pickup_location=pickup_location,
            order=order,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
            cache=cache,
        )
