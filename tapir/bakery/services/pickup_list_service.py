from dataclasses import dataclass, field

from tapir.bakery.models import (
    BreadsPerPickupLocationPerWeek,
    PreferredBread,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.utils.shortcuts import get_from_cache_or_compute


@dataclass
class PickupListMemberData:
    member_id: str
    member_name: str
    total: int = 0
    total_assigned: int = 0
    bread_counts: dict[str, int] = field(default_factory=dict)
    bread_preferred: dict[str, bool] = field(default_factory=dict)
    breads: list[dict] = field(default_factory=list)


class PickupListService:
    @classmethod
    def get_pickup_list(
        cls, year: int, week: int, pickup_location_id: str, cache: dict | None = None
    ) -> dict:
        if cache is None:
            cache = {}

        assigned_bread_names = cls._get_assigned_bread_names(
            year, week, pickup_location_id, cache
        )
        members_data = cls._collect_member_data(year, week, pickup_location_id, cache)
        cls._prime_preferred_breads(year, week, cache)
        preferred_by_member = cls._get_preferred_breads(members_data.keys(), cache)

        delivered_bread_names = set()
        for member_data in members_data.values():
            delivered_bread_names.update(member_data.bread_counts.keys())
        all_bread_names = sorted(assigned_bread_names | delivered_bread_names)

        cls._apply_preferences(members_data, preferred_by_member, all_bread_names)

        member_datas = sorted(
            members_data.values(),
            key=lambda member_data: member_data.member_name.lower(),
        )
        bread_totals, grand_total = cls._compute_totals(member_datas, all_bread_names)

        return {
            "bread_names": all_bread_names,
            "entries": member_datas,
            "bread_totals": bread_totals,
            "grand_total": grand_total,
        }

    @classmethod
    def _get_assigned_bread_names(
        cls, year: int, week: int, pickup_location_id: str, cache: dict
    ) -> set[str]:
        def compute():
            by_location = {}
            rows = BreadsPerPickupLocationPerWeek.objects.filter(
                year=year, delivery_week=week, bread__is_active=True
            ).select_related("bread")
            for row in rows:
                by_location.setdefault(row.pickup_location_id, set()).add(
                    row.bread.name
                )
            return by_location

        by_location = get_from_cache_or_compute(
            get_from_cache_or_compute(cache, "assigned_bread_names", lambda: {}),
            (year, week),
            compute,
        )
        return by_location.get(pickup_location_id, set())

    @classmethod
    def _collect_member_data(
        cls, year: int, week: int, pickup_location_id: str, cache: dict
    ) -> dict[str, PickupListMemberData]:
        deliveries = BreadDeliveryContextService.get_deliveries_for_location_for_week(
            year=year,
            delivery_week=week,
            pickup_location_id=pickup_location_id,
            cache=cache,
        )

        members_data: dict[str, PickupListMemberData] = {}
        for delivery in deliveries:
            member = delivery.subscription.member
            if member.id not in members_data:
                members_data[member.id] = PickupListMemberData(
                    member_id=member.id,
                    member_name=cls._get_display_name(member),
                )
            member_data = members_data[member.id]

            member_data.total += 1

            if delivery.bread:
                bread_name = delivery.bread.name
                member_data.bread_counts[bread_name] = (
                    member_data.bread_counts.get(bread_name, 0) + 1
                )
                member_data.total_assigned += 1
                member_data.breads.append(
                    {"delivery_id": str(delivery.id), "bread_name": bread_name}
                )

        return members_data

    @classmethod
    def _get_display_name(cls, member) -> str:
        if member.pseudonym:
            return member.pseudonym
        if member.last_name:
            return f"{member.last_name[0]}., {member.first_name}"
        return member.first_name or "Unbekannt"

    @classmethod
    def _prime_preferred_breads(cls, year: int, week: int, cache: dict):
        primed = get_from_cache_or_compute(
            cache, "preferred_breads_primed", lambda: set()
        )
        if (year, week) in primed:
            return
        primed.add((year, week))

        grouped = BreadDeliveryContextService.get_deliveries_by_location_for_week(
            year=year, delivery_week=week, cache=cache
        )
        member_ids = {
            delivery.subscription.member_id
            for deliveries in grouped.values()
            for delivery in deliveries
        }
        cls._get_preferred_breads(member_ids, cache)

    @classmethod
    def _get_preferred_breads(cls, member_ids, cache: dict) -> dict[str, set[str]]:
        preferred_by_member = get_from_cache_or_compute(
            cache, "preferred_bread_names_by_member_id", lambda: {}
        )
        missing = set(member_ids) - set(preferred_by_member)
        for member_id in missing:
            preferred_by_member[member_id] = set()
        for preferred_bread in PreferredBread.objects.filter(
            member_id__in=missing
        ).prefetch_related("breads"):
            preferred_by_member[preferred_bread.member_id] = {
                bread.name for bread in preferred_bread.breads.all()
            }
        return preferred_by_member

    @classmethod
    def _apply_preferences(
        cls,
        members_data: dict[str, PickupListMemberData],
        preferred_by_member: dict[str, set[str]],
        all_bread_names: list[str],
    ):
        for member_id, member_data in members_data.items():
            member_preferences = preferred_by_member.get(member_id, set())
            for bread_name in all_bread_names:
                has_delivery = member_data.bread_counts.get(bread_name, 0) > 0
                member_data.bread_preferred[bread_name] = (
                    bread_name in member_preferences and not has_delivery
                )

    @classmethod
    def _compute_totals(
        cls, member_datas: list[PickupListMemberData], all_bread_names: list[str]
    ) -> tuple[dict, int]:
        bread_totals = {
            bread_name: sum(
                member_data.bread_counts.get(bread_name, 0)
                for member_data in member_datas
            )
            for bread_name in all_bread_names
        }
        grand_total = sum(member_data.total for member_data in member_datas)
        return bread_totals, grand_total
