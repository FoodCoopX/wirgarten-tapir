from typing import Any

from tapir.bakery.models import BreadsPerPickupLocationPerWeek
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.pickup_locations.models import PickupLocation
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)


class DistributionListService:
    @staticmethod
    def get_distribution_list(year: int, week: int, day: int) -> dict[str, Any]:
        cache = {}
        location_ids = (
            PickupLocationDeliveryDayService.get_pickup_location_ids_for_delivery_day(
                day=day, cache=cache
            )
        )
        day_locations = list(PickupLocation.objects.filter(id__in=location_ids))

        # 1. Check for solver results
        bread_counts = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id__in=location_ids,
        ).select_related("bread", "pickup_location")

        # Evaluate once: .exists() ran its own SELECT without filling the
        # result cache, so iterating below re-ran the whole query.
        bread_counts = list(bread_counts)
        has_solver_results = bool(bread_counts)

        # 2. All deliveries for this year/week/day, grouped by the station
        # they resolve to. The service drops jokered slots, which are not
        # delivered and must not be counted.
        location_names_by_id = {pl.id: pl.name for pl in day_locations}
        deliveries_by_location = (
            BreadDeliveryContextService.get_deliveries_by_location_for_week(
                year=year, delivery_week=week, cache=cache
            )
        )

        # 3. Directly ordered breads (bread IS NOT NULL)
        # 4. Total deliveries per location (all slots)
        # Keyed by pickup location id, not by name: two stations that share a
        # name would otherwise collapse into a single Verteilliste row with
        # their loaves added together.
        ordered_by_location = {}
        total_deliveries_by_location = {}
        for location_id, deliveries in deliveries_by_location.items():
            if location_id not in location_names_by_id:
                continue
            total_deliveries_by_location[location_id] = (
                total_deliveries_by_location.get(location_id, 0) + len(deliveries)
            )
            for delivery in deliveries:
                if not delivery.bread:
                    continue
                bread_name = delivery.bread.name
                ordered_by_location.setdefault(location_id, {})
                ordered_by_location[location_id][bread_name] = (
                    ordered_by_location[location_id].get(bread_name, 0) + 1
                )

        if has_solver_results:
            # ---------- WITH SOLVER RESULTS ----------
            baked_by_location = {}
            for bc in bread_counts:
                location_id = bc.pickup_location_id
                bread_name = bc.bread.name if bc.bread else "Unbekannt"
                baked_by_location.setdefault(location_id, {})
                baked_by_location[location_id][bread_name] = (
                    baked_by_location[location_id].get(bread_name, 0) + bc.count
                )

            all_location_ids = sorted(
                set(list(baked_by_location.keys()) + list(ordered_by_location.keys())),
                key=lambda location_id: location_names_by_id.get(location_id, ""),
            )
            all_bread_names = sorted(
                set(
                    name
                    for breads in list(baked_by_location.values())
                    + list(ordered_by_location.values())
                    for name in breads.keys()
                )
            )

            locations = []
            for location_id in all_location_ids:
                loc_name = location_names_by_id.get(location_id, "Unbekannt")
                baked_breads = baked_by_location.get(location_id, {})
                ordered_breads = ordered_by_location.get(location_id, {})

                combined_breads = {}
                loc_bread_names = set(
                    list(baked_breads.keys()) + list(ordered_breads.keys())
                )
                for bread_name in loc_bread_names:
                    baked = baked_breads.get(bread_name, 0)
                    ordered = ordered_breads.get(bread_name, 0)
                    combined_breads[bread_name] = {
                        "baked": baked,
                        "ordered": ordered,
                        "extra": baked - ordered,
                    }

                total_baked = sum(b["baked"] for b in combined_breads.values())
                total_ordered = sum(b["ordered"] for b in combined_breads.values())

                locations.append(
                    {
                        "name": loc_name,
                        "breads": combined_breads,
                        "total_baked": total_baked,
                        "total_ordered": total_ordered,
                        "total_extra": total_baked - total_ordered,
                    }
                )

        else:
            # ---------- WITHOUT SOLVER RESULTS ----------
            # bread columns: only ordered count (no baked, no extra per bread)
            # totals: baked = total deliveries, ordered = sum of directly ordered
            # extra = total deliveries - directly ordered (= not yet chosen)

            all_location_ids = sorted(
                set(
                    list(ordered_by_location.keys())
                    + list(total_deliveries_by_location.keys())
                ),
                key=lambda location_id: location_names_by_id.get(location_id, ""),
            )
            all_bread_names = sorted(
                set(
                    name
                    for breads in ordered_by_location.values()
                    for name in breads.keys()
                )
            )

            locations = []
            for location_id in all_location_ids:
                loc_name = location_names_by_id.get(location_id, "Unbekannt")
                ordered_breads = ordered_by_location.get(location_id, {})
                loc_total_deliveries = total_deliveries_by_location.get(location_id, 0)
                loc_total_ordered = sum(ordered_breads.values())

                combined_breads = {}
                for bread_name in ordered_breads:
                    combined_breads[bread_name] = {
                        "ordered": ordered_breads[bread_name],
                    }

                locations.append(
                    {
                        "name": loc_name,
                        "breads": combined_breads,
                        "total_baked": loc_total_deliveries,
                        "total_ordered": loc_total_ordered,
                        "total_extra": loc_total_deliveries - loc_total_ordered,
                    }
                )

        # 5. Build bread totals
        bread_totals = {}
        for bread_name in all_bread_names:
            if has_solver_results:
                total_baked = sum(
                    loc["breads"].get(bread_name, {}).get("baked", 0)
                    for loc in locations
                )
            else:
                total_baked = 0
            total_ordered = sum(
                loc["breads"].get(bread_name, {}).get("ordered", 0) for loc in locations
            )
            bread_totals[bread_name] = {
                "baked": total_baked,
                "ordered": total_ordered,
                "extra": total_baked - total_ordered if has_solver_results else 0,
            }

        grand_total_baked = sum(loc["total_baked"] for loc in locations)
        grand_total_ordered = sum(loc["total_ordered"] for loc in locations)

        return {
            "has_solver_results": has_solver_results,
            "locations": locations,
            "bread_names": all_bread_names,
            "bread_totals": bread_totals,
            "grand_total_baked": grand_total_baked,
            "grand_total_ordered": grand_total_ordered,
            "grand_total_extra": grand_total_baked - grand_total_ordered,
        }
