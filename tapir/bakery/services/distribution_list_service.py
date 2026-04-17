from typing import Any

from django.db.models import OuterRef, Subquery

from tapir.bakery.models import BreadDelivery, BreadsPerPickupLocationPerWeek
from tapir.pickup_locations.models import PickupLocation
from tapir.wirgarten.models import PickupLocationOpeningTime


class DistributionListService:
    @staticmethod
    def get_distribution_list(year: int, week: int, day: int) -> dict[str, Any]:
        # Efficient query: get pickup locations with their first delivery day
        first_day_subquery = (
            PickupLocationOpeningTime.objects.filter(pickup_location=OuterRef("pk"))
            .order_by("day_of_week")
            .values("day_of_week")[:1]
        )

        day_locations = list(
            PickupLocation.objects.annotate(
                first_delivery_day=Subquery(first_day_subquery)
            ).filter(first_delivery_day=day)
        )
        location_ids = [pl.id for pl in day_locations]

        # 1. Check for solver results
        bread_counts = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id__in=location_ids,
        ).select_related("bread", "pickup_location")

        has_solver_results = bread_counts.exists()

        # 2. All deliveries for this year/week/day
        all_deliveries = BreadDelivery.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id__in=location_ids,
        ).select_related("pickup_location", "bread")

        # 3. Directly ordered breads (bread IS NOT NULL)
        ordered_by_location = {}
        for delivery in all_deliveries:
            if not delivery.pickup_location or not delivery.bread:
                continue
            loc_name = delivery.pickup_location.name
            bread_name = delivery.bread.name
            ordered_by_location.setdefault(loc_name, {})
            ordered_by_location[loc_name][bread_name] = (
                ordered_by_location[loc_name].get(bread_name, 0) + 1
            )

        # 4. Total deliveries per location (all slots)
        total_deliveries_by_location = {}
        for delivery in all_deliveries:
            if not delivery.pickup_location:
                continue
            loc_name = delivery.pickup_location.name
            total_deliveries_by_location[loc_name] = (
                total_deliveries_by_location.get(loc_name, 0) + 1
            )

        if has_solver_results:
            # ---------- WITH SOLVER RESULTS ----------
            baked_by_location = {}
            for bc in bread_counts:
                loc_name = bc.pickup_location.name
                bread_name = bc.bread.name if bc.bread else "Unbekannt"
                baked_by_location.setdefault(loc_name, {})
                baked_by_location[loc_name][bread_name] = (
                    baked_by_location[loc_name].get(bread_name, 0) + bc.count
                )

            all_location_names = sorted(
                set(list(baked_by_location.keys()) + list(ordered_by_location.keys()))
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
            for loc_name in all_location_names:
                baked_breads = baked_by_location.get(loc_name, {})
                ordered_breads = ordered_by_location.get(loc_name, {})

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

            all_location_names = sorted(
                set(
                    list(ordered_by_location.keys())
                    + list(total_deliveries_by_location.keys())
                )
            )
            all_bread_names = sorted(
                set(
                    name
                    for breads in ordered_by_location.values()
                    for name in breads.keys()
                )
            )

            locations = []
            for loc_name in all_location_names:
                ordered_breads = ordered_by_location.get(loc_name, {})
                loc_total_deliveries = total_deliveries_by_location.get(loc_name, 0)
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
