from tapir.bakery.models import (
    BreadDelivery,
    BreadsPerPickupLocationPerWeek,
    PreferredBread,
)


class PickupListService:
    @staticmethod
    def get_pickup_list(year: int, week: int, pickup_location_id: str) -> dict:
        """
        Returns:
        {
            "bread_names": ["Dinkelkruste", "Roggenbrot", ...],
            "entries": [
                {
                    "member_id": "uuid",
                    "member_name": "M., Anna",
                    "bread_counts": {"Roggenbrot": 2, "Dinkelkruste": 0},
                    "bread_preferred": {"Roggenbrot": False, "Dinkelkruste": True},
                    "total": 3,          # total delivery slots (assigned + unassigned)
                    "total_assigned": 2,  # only slots with a bread assigned
                    "breads": [
                        {"delivery_id": "uuid", "bread_name": "Roggenbrot"},
                        ...
                    ],
                },
                ...
            ],
            "bread_totals": {"Roggenbrot": 5, "Dinkelkruste": 3},
            "grand_total": 8,
        }
        Sorted by member_name.
        """
        assigned_bread_names = PickupListService._get_assigned_bread_names(
            year, week, pickup_location_id
        )
        members_data, member_ids = PickupListService._collect_member_data(
            year, week, pickup_location_id
        )
        preferred_by_member = PickupListService._get_preferred_breads(member_ids)

        delivery_bread_names = set()
        for entry in members_data.values():
            delivery_bread_names.update(entry["bread_counts"].keys())
        all_bread_names = sorted(set(assigned_bread_names) | delivery_bread_names)

        PickupListService._apply_preferences(
            members_data, preferred_by_member, all_bread_names
        )

        entries = sorted(members_data.values(), key=lambda x: x["member_name"].lower())
        bread_totals, grand_total = PickupListService._compute_totals(
            entries, all_bread_names
        )

        return {
            "bread_names": all_bread_names,
            "entries": entries,
            "bread_totals": bread_totals,
            "grand_total": grand_total,
        }

    @staticmethod
    def _get_assigned_bread_names(
        year: int, week: int, pickup_location_id: str
    ) -> list[str]:
        assigned_breads = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id=pickup_location_id,
        ).select_related("bread")

        return sorted(set(bc.bread.name for bc in assigned_breads if bc.bread))

    @staticmethod
    def _collect_member_data(
        year: int, week: int, pickup_location_id: str
    ) -> tuple[dict, set]:
        deliveries = BreadDelivery.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id=pickup_location_id,
            joker_taken=False,
        ).select_related(
            "subscription__member",
            "bread",
        )

        member_ids = set()
        members_data = {}

        for delivery in deliveries:
            member = delivery.subscription.member
            member_id = str(member.id)
            member_ids.add(member.id)

            if member_id not in members_data:
                members_data[member_id] = {
                    "member_id": member_id,
                    "member_name": PickupListService._get_display_name(member),
                    "bread_counts": {},
                    "bread_preferred": {},
                    "total": 0,
                    "total_assigned": 0,
                    "breads": [],
                }

            members_data[member_id]["total"] += 1

            bread_name = delivery.bread.name if delivery.bread else None
            if bread_name:
                members_data[member_id]["bread_counts"][bread_name] = (
                    members_data[member_id]["bread_counts"].get(bread_name, 0) + 1
                )
                members_data[member_id]["total_assigned"] += 1
                members_data[member_id]["breads"].append(
                    {
                        "delivery_id": str(delivery.id),
                        "bread_name": bread_name,
                    }
                )

        return members_data, member_ids

    @staticmethod
    def _get_display_name(member) -> str:
        pseudonym = getattr(member, "pseudonym", None)
        if pseudonym:
            return pseudonym
        last_name = getattr(member, "last_name", "")
        first_name = getattr(member, "first_name", "")
        if last_name:
            return f"{last_name[0]}., {first_name}"
        return first_name or "Unbekannt"

    @staticmethod
    def _get_preferred_breads(member_ids: set) -> dict[str, set[str]]:
        preferred_by_member = {}
        if member_ids:
            preferred_entries = PreferredBread.objects.filter(
                member_id__in=member_ids
            ).prefetch_related("breads")

            for pref in preferred_entries:
                preferred_by_member[str(pref.member_id)] = set(
                    b.name for b in pref.breads.all()
                )
        return preferred_by_member

    @staticmethod
    def _apply_preferences(
        members_data: dict,
        preferred_by_member: dict[str, set[str]],
        all_bread_names: list[str],
    ):
        for member_id, entry in members_data.items():
            member_prefs = preferred_by_member.get(member_id, set())
            for bread_name in all_bread_names:
                has_delivery = entry["bread_counts"].get(bread_name, 0) > 0
                is_preferred = bread_name in member_prefs
                entry["bread_preferred"][bread_name] = is_preferred and not has_delivery

    @staticmethod
    def _compute_totals(
        entries: list[dict], all_bread_names: list[str]
    ) -> tuple[dict, int]:
        bread_totals = {}
        for bread_name in all_bread_names:
            bread_totals[bread_name] = sum(
                e["bread_counts"].get(bread_name, 0) for e in entries
            )
        grand_total = sum(e["total"] for e in entries)
        return bread_totals, grand_total
