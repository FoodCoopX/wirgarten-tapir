from tapir.bakery.models import BreadDelivery, BreadsPerPickupLocationPerWeek
from tapir.pickup_locations.models import PickupLocation


class VerteillisteService:
    @staticmethod
    def get_verteilliste(year: int, week: int, day: int) -> dict:
        """
        Returns:
        {
            "has_solver_results": True,
            "locations": [{"name": "Markt", "breads": {"Roggenbrot": 5}, "total": 5}, ...],
            "bread_names": ["Dinkelkruste", "Roggenbrot"],
            "bread_totals": {"Roggenbrot": 10, "Dinkelkruste": 5},
            "grand_total": 15,
        }
        """
        day_locations = [
            pl
            for pl in PickupLocation.objects.all()
            if getattr(pl, "delivery_day", None) == day
        ]
        location_ids = [pl.id for pl in day_locations]

        bread_counts = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id__in=location_ids,
        ).select_related("bread", "pickup_location")

        has_solver_results = bread_counts.exists()
        location_breads = {}

        if has_solver_results:
            for bc in bread_counts:
                loc_name = bc.pickup_location.name
                bread_name = bc.bread.name if bc.bread else "Unbekannt"
                location_breads.setdefault(loc_name, {})
                location_breads[loc_name][bread_name] = (
                    location_breads[loc_name].get(bread_name, 0) + bc.count
                )
        else:
            # Fallback: count BreadDelivery objects per pickup location
            # Before solver runs, breads are not assigned yet, so we just
            # count delivery slots (= number of breads to be delivered)
            deliveries = BreadDelivery.objects.filter(
                year=year,
                delivery_week=week,
                pickup_location_id__in=location_ids,
            ).select_related("pickup_location", "bread")

            for delivery in deliveries:
                if not delivery.pickup_location:
                    continue
                loc_name = delivery.pickup_location.name
                location_breads.setdefault(loc_name, {})

                if delivery.bread:
                    # Bread already assigned (partial solver run?)
                    bread_name = delivery.bread.name
                else:
                    # No bread assigned yet — count as generic slot
                    bread_name = "Brotlieferung (noch nicht zugewiesen)"

                location_breads[loc_name][bread_name] = (
                    location_breads[loc_name].get(bread_name, 0) + 1
                )

        bread_names = sorted(
            set(name for breads in location_breads.values() for name in breads.keys())
        )

        locations = sorted(
            [
                {
                    "name": loc_name,
                    "breads": breads,
                    "total": sum(breads.values()),
                }
                for loc_name, breads in location_breads.items()
            ],
            key=lambda l: l["name"],
        )

        bread_totals = {}
        for bread_name in bread_names:
            bread_totals[bread_name] = sum(
                loc["breads"].get(bread_name, 0) for loc in locations
            )

        grand_total = sum(loc["total"] for loc in locations)

        return {
            "has_solver_results": has_solver_results,
            "locations": locations,
            "bread_names": bread_names,
            "bread_totals": bread_totals,
            "grand_total": grand_total,
        }
