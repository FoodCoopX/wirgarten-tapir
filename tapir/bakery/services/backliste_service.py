from tapir.bakery.models import BreadsPerPickupLocationPerWeek, StoveSession
from tapir.pickup_locations.models import PickupLocation


class BacklisteService:
    @staticmethod
    def get_pickup_location_ids_for_day(day: int) -> list:
        """Filter pickup locations by delivery_day property (not a DB field)."""
        return [
            pl.id
            for pl in PickupLocation.objects.all()
            if getattr(pl, "delivery_day", None) == day
        ]

    @staticmethod
    def get_backliste(year: int, week: int, day: int) -> dict:
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
        location_ids = BacklisteService.get_pickup_location_ids_for_day(day)

        bread_counts = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id__in=location_ids,
        ).select_related("bread")

        stove_sessions = (
            StoveSession.objects.filter(
                year=year,
                delivery_week=week,
                delivery_day=day,
            )
            .select_related("bread")
            .order_by("session_number", "layer_number")
        )

        # Build bread summary
        bread_map = {}
        for bc in bread_counts:
            name = bc.bread.name if bc.bread else "Unbekannt"
            bread_map.setdefault(name, {"deliveries": 0, "baked": 0})
            bread_map[name]["deliveries"] += bc.count

        for ss in stove_sessions:
            name = ss.bread.name if ss.bread else None
            if name:
                bread_map.setdefault(name, {"deliveries": 0, "baked": 0})
                bread_map[name]["baked"] += ss.quantity

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
            s["layers"].sort(key=lambda l: l["layer"])

        return {
            "breads": breads,
            "total_deliveries": total_deliveries,
            "total_baked": total_baked,
            "total_extra": total_baked - total_deliveries,
            "stove_sessions": sorted_sessions,
        }
