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
    Collect per-member preference data for the solver.

    Only counts members whose deliveries have bread=None (solver-assigned).
    Members who directly chose a bread (bread is not None) are excluded because
    the solver already handles them via fixed_demand.

    Returns a list of dicts, each with:
        - member_id: int
        - location_id: int
        - preferred_bread_ids: list[int]   (1–3 bread IDs)
    """
    # The solver run's cache when it threads one in, so the pickup-location
    # history and the joker map are not loaded twice.
    if cache is None:
        cache = {}

    # The station is derived from the member's pickup-location history, and
    # jokered slots are dropped.
    deliveries_by_location = (
        BreadDeliveryContextService.get_deliveries_by_location_for_week(
            year=year,
            delivery_week=delivery_week,
            cache=cache,
            queryset=BreadDelivery.objects.filter(
                bread__isnull=True,
                subscription__product__type__is_bread=True,
            ),
            delivery_day=delivery_day,
        )
    )

    if not deliveries_by_location:
        return []

    # Build member -> set of pickup_location_ids (from their unassigned deliveries)
    member_locations: dict[int, set[int]] = defaultdict(set)
    for location_id, location_deliveries in deliveries_by_location.items():
        for d in location_deliveries:
            member_locations[d.subscription.member_id].add(location_id)

    if not member_locations:
        return []

    # Get preferred breads for these members
    preferred_qs = PreferredBread.objects.filter(
        member_id__in=member_locations.keys()
    ).prefetch_related("breads")

    result = []
    for pref in preferred_qs:
        member_id = pref.member_id
        # Read through the prefetch cache: any queryset method other than
        # .all() on a prefetched related manager builds a fresh queryset and
        # ignores it, costing one query per member.
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
