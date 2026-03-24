from tapir.bakery.models import (
    BreadDelivery,
    BreadsPerPickupLocationPerWeek,
    PreferredBread,
)


class AbhollisteService:
    @staticmethod
    def get_abholliste(year: int, week: int, pickup_location_id: str) -> dict:
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
        # 1. Get all bread types assigned to this pickup location for this week
        assigned_breads = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id=pickup_location_id,
        ).select_related("bread")

        assigned_bread_names = sorted(
            set(bc.bread.name for bc in assigned_breads if bc.bread)
        )

        # 2. Get all deliveries for this location
        deliveries = BreadDelivery.objects.filter(
            year=year,
            delivery_week=week,
            pickup_location_id=pickup_location_id,
            joker_taken=False,  # Exclude jokers from the abholliste
        ).select_related(
            "subscription__member",
            "bread",
        )

        # 3. Collect all member data from deliveries
        member_ids = set()
        members_data = {}

        for delivery in deliveries:
            member = delivery.subscription.member
            member_id = str(member.id)
            member_ids.add(member.id)

            if member_id not in members_data:
                pseudonym = getattr(member, "pseudonym", None)
                if pseudonym:
                    display_name = pseudonym
                else:
                    last_name = getattr(member, "last_name", "")
                    first_name = getattr(member, "first_name", "")
                    if last_name:
                        display_name = f"{last_name[0]}., {first_name}"
                    else:
                        display_name = first_name or "Unbekannt"

                members_data[member_id] = {
                    "member_id": member_id,
                    "member_name": display_name,
                    "bread_counts": {},
                    "bread_preferred": {},
                    "total": 0,
                    "total_assigned": 0,
                    "breads": [],
                }

            # Count every delivery slot for the member
            members_data[member_id]["total"] += 1

            # Track assigned breads separately
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

        # 4. Get preferred breads for all members with deliveries
        preferred_by_member = {}
        if member_ids:
            preferred_entries = PreferredBread.objects.filter(
                member_id__in=member_ids
            ).prefetch_related("breads")

            for pref in preferred_entries:
                preferred_by_member[str(pref.member_id)] = set(
                    b.name for b in pref.breads.all()
                )

        # 5. Also collect bread names from deliveries (in case solver hasn't run)
        delivery_bread_names = set()
        for entry in members_data.values():
            delivery_bread_names.update(entry["bread_counts"].keys())

        # Combine: assigned breads + any bread names from deliveries
        all_bread_names = sorted(set(assigned_bread_names) | delivery_bread_names)

        # 6. Build bread_preferred for each member
        for member_id, entry in members_data.items():
            member_prefs = preferred_by_member.get(member_id, set())
            for bread_name in all_bread_names:
                has_delivery = entry["bread_counts"].get(bread_name, 0) > 0
                is_preferred = bread_name in member_prefs
                entry["bread_preferred"][bread_name] = is_preferred and not has_delivery

        # 7. Compute totals
        entries = sorted(members_data.values(), key=lambda x: x["member_name"].lower())

        bread_totals = {}
        for bread_name in all_bread_names:
            bread_totals[bread_name] = sum(
                e["bread_counts"].get(bread_name, 0) for e in entries
            )

        grand_total = sum(e["total"] for e in entries)

        return {
            "bread_names": all_bread_names,
            "entries": entries,
            "bread_totals": bread_totals,
            "grand_total": grand_total,
        }
