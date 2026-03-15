from collections import defaultdict

from tapir.bakery.models import BreadDelivery, PreferredBread


def get_member_preferences(
    year: int,
    delivery_week: int,
    delivery_day: int | None = None,
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
    deliveries_qs = BreadDelivery.objects.filter(
        year=year,
        delivery_week=delivery_week,
        bread__isnull=True,
        pickup_location__isnull=False,
    ).select_related("pickup_location", "subscription__member")

    deliveries = list(deliveries_qs)

    # Filter by delivery_day in Python — it's a @property, not a DB field
    if delivery_day is not None:
        deliveries = [
            d for d in deliveries if d.pickup_location.delivery_day == delivery_day
        ]

    if not deliveries:
        return []

    # Build member -> set of pickup_location_ids (from their unassigned deliveries)
    member_locations: dict[int, set[int]] = defaultdict(set)
    for d in deliveries:
        member_locations[d.subscription.member_id].add(d.pickup_location_id)

    if not member_locations:
        return []

    # Get preferred breads for these members
    preferred_qs = PreferredBread.objects.filter(
        member_id__in=member_locations.keys()
    ).prefetch_related("breads")

    result = []
    for pref in preferred_qs:
        member_id = pref.member_id
        bread_ids = list(pref.breads.values_list("id", flat=True))
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
