import datetime

from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
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
        cache: dict,
    ) -> bool:
        if (
            already_registered_member
            and MemberPickupLocationGetter.get_member_pickup_location_id(
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
