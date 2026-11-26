from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    BreadSpecificsPerDeliveryDay,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)

CAPACITY_SOURCE_FIXED = "fixed"
CAPACITY_SOURCE_DAY_MAX = "day_max"
CAPACITY_SOURCE_GROUP_MAX = "group_max"
CAPACITY_SOURCE_BREAD_MAX = "bread_max"


@dataclass
class BreadDirectOrderLimit:
    bread_id: str
    bread_name: str
    group_id: str | None
    group_name: str | None
    # None when nothing bounds the bread that day: then it has no limit.
    total_capacity: int | None
    total_capacity_source: str | None
    min_remaining: int
    default_percent: int
    percent: int
    limit: int | None
    ordered: int
    # The part of the day's Min. Stück that neither the orders nor Min. Rest
    # cover. It is baked anyway, which matters only within a group.
    open_min_pieces: int


@dataclass
class GroupDirectOrderLimit:
    group_id: str
    group_name: str
    # The breads that share the group's limit: those without a fixed amount.
    bread_ids: list[str]
    # The group's max, and what its breads with a fixed amount take of it.
    max_pieces: int | None
    fixed_pieces: int
    # max_pieces less fixed_pieces, None without a max.
    total_capacity: int | None
    min_remaining: int
    # The sum of its breads' open_min_pieces: baked anyway, so held back like
    # Min. Rest.
    open_min_pieces: int
    percent: int
    limit: int | None
    ordered: int


@dataclass
class DayDirectOrderLimits:
    breads: dict[str, BreadDirectOrderLimit]
    # Only groups with more than one bread that day and at least one without a
    # fixed amount.
    groups: dict[str, GroupDirectOrderLimit]

    def remaining(self, bread_id: str) -> int | None:
        """
        None means unlimited. A bread not offered that day has nothing left.
        A bread with a fixed amount does not share its group's limit.
        """
        bread = self.breads.get(bread_id)
        if bread is None:
            return 0
        remainders = []
        if bread.limit is not None:
            remainders.append(bread.limit - bread.ordered)
        group = self.groups.get(bread.group_id)
        if (
            group is not None
            and group.limit is not None
            and bread_id in group.bread_ids
        ):
            group_left = group.limit - group.ordered
            # Orders of the bread up to its own open minimum are baked anyway,
            # so they take nothing from the group's other breads.
            remainders.append(
                group_left + bread.open_min_pieces if group_left >= 0 else group_left
            )
        return max(min(remainders), 0) if remainders else None


class DirectOrderLimitService:
    """
    How many loaves of a bread members may choose directly for one delivery
    day, counted over all stations delivered that day.

    The limit is a percentage of the day's capacity less Min. Rest, rounded
    down. The capacity is, in this order: the day's fixed pieces, the day's
    max pieces, the group's max when the bread shares its group with other
    breads that day, the bread's own max. Without any of them the bread has
    no limit. The percentage is the day's, else the bread's.

    A group with several breads that day also has a limit of its own. As in
    the solver (C15 in solver_model), the group's max (the smallest max of
    its breads) bounds everything the group bakes, the fixed amounts of its
    breads included, so those come off first. What is left is shared by the
    breads without a fixed amount, less the sum of their Min. Rest and of
    the day minimums their own orders do not fill yet, at the highest
    percentage among them, so no bread's own percentage is cut by the
    group's. A bread with a fixed amount is bounded by that amount alone.
    """

    @classmethod
    def compute_limit(
        cls, percent: int, capacity: int | None, min_remaining: int
    ) -> int | None:
        if capacity is None:
            return None
        return percent * max(capacity - min_remaining, 0) // 100

    @classmethod
    def get_limits_for_day(
        cls,
        year: int,
        delivery_week: int,
        delivery_day: int,
        cache: dict,
        exclude_delivery_ids: Collection[str] = (),
    ) -> DayDirectOrderLimits:
        """
        exclude_delivery_ids leaves deliveries out of the counts, so a member
        changing a choice does not count against the bread they leave.
        """
        breads = [
            entry.bread
            for entry in AvailableBreadsForDeliveryDay.objects.filter(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                bread__is_active=True,
            )
            .select_related("bread", "bread__group")
            .order_by("bread__name")
        ]
        specifics_by_bread_id = {
            specifics.bread_id: specifics
            for specifics in BreadSpecificsPerDeliveryDay.objects.filter(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                bread_id__in=[bread.id for bread in breads],
            )
        }
        # A jokered slot is not delivered, so it does not count.
        ordered = BreadDeliveryContextService.count_chosen_breads_for_delivery_day(
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
            cache=cache,
            bread_ids=[bread.id for bread in breads],
            exclude_delivery_ids=exclude_delivery_ids,
        )

        members_by_group_id = defaultdict(list)
        for bread in breads:
            if bread.group_id is not None:
                members_by_group_id[bread.group_id].append(bread)
        # A bread alone in its group that day is planned on its own values.
        members_by_group_id = {
            group_id: members
            for group_id, members in members_by_group_id.items()
            if len(members) > 1
        }
        group_max_pieces = {
            group_id: min(
                (b.max_pieces for b in members if b.max_pieces is not None),
                default=None,
            )
            for group_id, members in members_by_group_id.items()
        }
        group_fixed_pieces = {
            group_id: sum(
                cls._fixed_pieces(specifics_by_bread_id.get(b.id)) or 0 for b in members
            )
            for group_id, members in members_by_group_id.items()
        }
        group_capacities = {
            group_id: (
                max(max_pieces - group_fixed_pieces[group_id], 0)
                if max_pieces is not None
                else None
            )
            for group_id, max_pieces in group_max_pieces.items()
        }

        bread_limits = {}
        for bread in breads:
            specifics = specifics_by_bread_id.get(bread.id)
            capacity, capacity_source = cls._capacity(
                bread, specifics, group_capacities
            )
            min_remaining = (
                specifics.min_remaining_pieces
                if specifics and specifics.min_remaining_pieces is not None
                else (bread.min_remaining_pieces or 0)
            )
            percent = (
                specifics.max_direct_order_percent
                if specifics and specifics.max_direct_order_percent is not None
                else bread.max_direct_order_percent
            )
            bread_limits[bread.id] = BreadDirectOrderLimit(
                bread_id=bread.id,
                bread_name=bread.name,
                group_id=bread.group_id,
                group_name=bread.group.name if bread.group else None,
                total_capacity=capacity,
                total_capacity_source=capacity_source,
                min_remaining=min_remaining,
                default_percent=bread.max_direct_order_percent,
                percent=percent,
                limit=cls.compute_limit(percent, capacity, min_remaining),
                ordered=ordered[bread.id],
                open_min_pieces=max(
                    cls._day_min_pieces(specifics) - ordered[bread.id] - min_remaining,
                    0,
                ),
            )

        group_limits = {}
        for group_id, members in members_by_group_id.items():
            sharing = [
                bread_limits[bread.id]
                for bread in members
                if cls._fixed_pieces(specifics_by_bread_id.get(bread.id)) is None
            ]
            if not sharing:
                continue
            percent = max(limit.percent for limit in sharing)
            min_remaining = sum(limit.min_remaining for limit in sharing)
            open_min_pieces = sum(limit.open_min_pieces for limit in sharing)
            group_limits[group_id] = GroupDirectOrderLimit(
                group_id=group_id,
                group_name=members[0].group.name,
                bread_ids=[limit.bread_id for limit in sharing],
                max_pieces=group_max_pieces[group_id],
                fixed_pieces=group_fixed_pieces[group_id],
                total_capacity=group_capacities[group_id],
                min_remaining=min_remaining,
                open_min_pieces=open_min_pieces,
                percent=percent,
                limit=cls.compute_limit(
                    percent,
                    group_capacities[group_id],
                    min_remaining + open_min_pieces,
                ),
                ordered=sum(limit.ordered for limit in sharing),
            )

        return DayDirectOrderLimits(breads=bread_limits, groups=group_limits)

    @classmethod
    def _fixed_pieces(cls, specifics) -> int | None:
        return specifics.fixed_pieces if specifics else None

    @classmethod
    def _day_min_pieces(cls, specifics) -> int:
        """
        Only the day's: a grouped bread's own Min. Stück bounds the group's
        total from below, not the bread (see collect_solver_input).
        """
        return (specifics.min_pieces or 0) if specifics else 0

    @classmethod
    def _capacity(cls, bread, specifics, group_capacities: dict):
        if cls._fixed_pieces(specifics) is not None:
            return specifics.fixed_pieces, CAPACITY_SOURCE_FIXED
        if specifics and specifics.max_pieces is not None:
            return specifics.max_pieces, CAPACITY_SOURCE_DAY_MAX
        if bread.group_id in group_capacities:
            capacity = group_capacities[bread.group_id]
            return capacity, CAPACITY_SOURCE_GROUP_MAX if capacity is not None else None
        if bread.max_pieces is not None:
            return bread.max_pieces, CAPACITY_SOURCE_BREAD_MAX
        return None, None
