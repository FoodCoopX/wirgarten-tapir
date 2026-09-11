from typing import Any

from django.db.models import Q

from tapir.bakery.models import (
    BreadsPerPickupLocationPerWeek,
    BreadsToBakePerWeek,
    StoveSession,
)
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)


class BakingListService:
    @staticmethod
    def get_pickup_location_ids_for_day(day: int, cache: dict | None = None) -> list:
        return (
            PickupLocationDeliveryDayService.get_pickup_location_ids_for_delivery_day(
                day=day, cache={} if cache is None else cache
            )
        )

    @staticmethod
    def _rows_for_day(queryset, day: int | None) -> list:
        """
        A week is planned either as a whole or day by day, and both shapes can
        sit in the table at once. Rows for this day win; the whole-week rows
        (delivery_day IS NULL) are the fallback for days the day-by-day runs
        have not covered. Adding the two together would count the same loaves
        twice.
        """
        rows = list(queryset.filter(Q(delivery_day=day) | Q(delivery_day__isnull=True)))
        rows_for_day = [row for row in rows if row.delivery_day is not None]
        return rows_for_day or [row for row in rows if row.delivery_day is None]

    @staticmethod
    def get_baking_list(year: int, week: int, day: int) -> dict[str, Any]:
        """
        Returns:
        {
            "breads": [{"name": "Roggenbrot", "deliveries": 10, "baked": 12, "extra": 2}, ...],
            "total_deliveries": 10,
            "total_baked": 12,
            "total_extra": 2,
            "stove_sessions": [
                {"session": 1, "layers": [{"layer": 1, "bread_name": "Roggenbrot", "quantity": 6}, ...]},
                ...
            ],
        }
        """
        location_ids = BakingListService.get_pickup_location_ids_for_day(day)

        bread_counts = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id__in=location_ids,
        ).select_related("bread")

        stove_sessions = BakingListService._rows_for_day(
            StoveSession.objects.filter(year=year, delivery_week=week)
            .select_related("bread")
            .order_by("session_number", "layer_number"),
            day,
        )

        # Build bread summary
        bread_map = {}
        for bc in bread_counts:
            name = bc.bread.name if bc.bread else "Unbekannt"
            bread_map.setdefault(name, {"deliveries": 0, "baked": 0})
            bread_map[name]["deliveries"] += bc.count

        # "baked" is what the solver decided to bake rather than the sum of the
        # stove layers: a bread with fixed_pieces occupies no layers.
        to_bake = BakingListService._rows_for_day(
            BreadsToBakePerWeek.objects.filter(
                year=year, delivery_week=week
            ).select_related("bread"),
            day,
        )
        for row in to_bake:
            name = row.bread.name if row.bread else None
            if name:
                bread_map.setdefault(name, {"deliveries": 0, "baked": 0})
                bread_map[name]["baked"] += row.quantity

        breads = sorted(
            [
                {
                    "name": name,
                    "deliveries": data["deliveries"],
                    "baked": data["baked"],
                    "extra": data["baked"] - data["deliveries"],
                }
                for name, data in bread_map.items()
            ],
            key=lambda b: b["name"],
        )

        total_deliveries = sum(b["deliveries"] for b in breads)
        total_baked = sum(b["baked"] for b in breads)

        # Build stove session groups
        session_groups = {}
        for ss in stove_sessions:
            session_groups.setdefault(
                ss.session_number, {"session": ss.session_number, "layers": []}
            )
            session_groups[ss.session_number]["layers"].append(
                {
                    "layer": ss.layer_number,
                    "bread_name": ss.bread.name if ss.bread else None,
                    "quantity": ss.quantity,
                }
            )
        sorted_sessions = sorted(session_groups.values(), key=lambda s: s["session"])
        for s in sorted_sessions:
            s["layers"].sort(key=lambda layer: layer["layer"])

        return {
            "breads": breads,
            "total_deliveries": total_deliveries,
            "total_baked": total_baked,
            "total_extra": total_baked - total_deliveries,
            "stove_sessions": sorted_sessions,
        }
