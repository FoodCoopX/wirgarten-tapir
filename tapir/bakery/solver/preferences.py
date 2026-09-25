from collections import defaultdict

from tapir.bakery.models import BreadDelivery, PreferredBread
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)


def get_member_preferences(
    year: int,
    delivery_week: int,
    delivery_day: int | None = None,
    cache: dict | None = None,
) -> list[dict]:
    """
    Only members whose deliveries have bread=None: a bread the member chose
    directly is already handled by the solver as fixed_demand.

    Each entry: member_id, location_id, preferred_bread_ids.
    """
    if cache is None:
        cache = {}

    deliveries_by_location = (
        BreadDeliveryContextService.get_deliveries_by_location_for_week(
            year=year,
            delivery_week=delivery_week,
            cache=cache,
            queryset=BreadDelivery.objects.filter(bread__isnull=True),
            delivery_day=delivery_day,
        )
    )

    if not deliveries_by_location:
        return []

    member_locations: dict[int, set[int]] = defaultdict(set)
    for location_id, location_deliveries in deliveries_by_location.items():
        for d in location_deliveries:
            member_locations[d.subscription.member_id].add(location_id)

    if not member_locations:
        return []

    preferred_qs = PreferredBread.objects.filter(
        member_id__in=member_locations.keys()
    ).prefetch_related("breads")

    result = []
    for pref in preferred_qs:
        member_id = pref.member_id
        # .all() reads the prefetch cache; any other method queries per member.
        bread_ids = [bread.id for bread in pref.breads.all()]
        if not bread_ids:
            continue
        for loc_id in member_locations.get(member_id, set()):
            result.append(
                {
                    "member_id": member_id,
                    "location_id": loc_id,
                    "preferred_bread_ids": bread_ids,
                }
            )

    return result
