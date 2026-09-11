from tapir.bakery.models import PreferredBread
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)


class PreferredBreadStatisticsService:
    """How many members with a delivery this week prefer each bread."""

    @classmethod
    def get_statistics(
        cls,
        year: int,
        delivery_week: int,
        delivery_day: int | None,
        cache: dict,
    ) -> dict:

        # Get all members with deliveries this week
        deliveries_by_location = (
            BreadDeliveryContextService.get_deliveries_by_location_for_week(
                year=year,
                delivery_week=delivery_week,
                cache=cache,
                delivery_day=delivery_day,
            )
        )
        deliveries = [d for ds in deliveries_by_location.values() for d in ds]

        # Unique members with deliveries
        member_ids = list(set(d.subscription.member_id for d in deliveries))
        total_members = len(member_ids)

        # Get preferred breads for these members
        preferred_qs = PreferredBread.objects.filter(
            member_id__in=member_ids
        ).prefetch_related("breads")

        members_with_preferences = 0
        members_without_preferences = 0
        bread_counts: dict[str, int] = {}

        for pref in preferred_qs:
            bread_list = list(pref.breads.all())
            if bread_list:
                members_with_preferences += 1
                for bread in bread_list:
                    bread_counts[bread.name] = bread_counts.get(bread.name, 0) + 1
            else:
                members_without_preferences += 1

        # Members with no PreferredBread entry at all
        members_with_pref_entry = set(p.member_id for p in preferred_qs)
        members_without_preferences += sum(
            1 for m_id in member_ids if m_id not in members_with_pref_entry
        )

        # Sort by count descending
        bread_statistics = sorted(
            [
                {
                    "bread_name": name,
                    "count": count,
                    "percentage": (
                        round(count / total_members * 100, 1)
                        if total_members > 0
                        else 0
                    ),
                }
                for name, count in bread_counts.items()
            ],
            key=lambda x: x["count"],
            reverse=True,
        )

        return {
            "total_members": total_members,
            "members_with_preferences": members_with_preferences,
            "members_without_preferences": members_without_preferences,
            "breads": bread_statistics,
        }
