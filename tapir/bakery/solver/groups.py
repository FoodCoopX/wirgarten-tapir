from dataclasses import replace

from tapir.bakery.solver.dataclasses import BreadInfo


def limit_groups(breads: list[BreadInfo]) -> dict[str, list[BreadInfo]]:
    """
    After resolve_groups: the breads of each group available on this day,
    fixed amount or not. Together they stay within the group's limits.
    """
    groups: dict[str, list[BreadInfo]] = {}
    for bread in breads:
        if bread.group_id is not None:
            groups.setdefault(bread.group_id, []).append(bread)
    return groups


def stove_groups(breads: list[BreadInfo]) -> dict[str, list[BreadInfo]]:
    """
    The groups that have at least two breads in the oven on this baking day,
    which may share its layers. A fixed_pieces bread occupies no stove layer;
    resolve_groups has already moved the grouped ones that can share a layer
    into the oven.
    """
    groups: dict[str, list[BreadInfo]] = {}
    for bread in breads:
        if bread.group_id is None or bread.fixed_pieces is not None:
            continue
        groups.setdefault(bread.group_id, []).append(bread)
    return {
        group_id: members for group_id, members in groups.items() if len(members) > 1
    }


def can_share_a_layer(bread: BreadInfo, others: list[BreadInfo]) -> bool:
    """Whether another of these breads allows one of its counts per layer."""
    counts = set(bread.pieces_per_stove_layer)
    return any(
        counts & set(other.pieces_per_stove_layer)
        for other in others
        if other.bread_id != bread.bread_id
    )


def resolve_groups(breads: list[BreadInfo]) -> list[BreadInfo]:
    """
    A bread alone in its group on this day becomes an ungrouped one: as for
    any ungrouped bread, its settings for the day replace its own values. A
    fixed_pieces bread keeps no min/max: the fixed amount overrides them.

    A grouped bread with a fixed amount counts toward its group. It goes into
    the oven with exactly that amount when it can share a layer with another
    bread of the group; otherwise it is baked outside the oven as before.
    """
    members_by_group = limit_groups(breads)
    resolved = []
    for bread in breads:
        members = members_by_group.get(bread.group_id, [])
        if len(members) > 1:
            if bread.fixed_pieces is not None and can_share_a_layer(bread, members):
                bread = replace(
                    bread,
                    fixed_pieces=None,
                    min_pieces=bread.fixed_pieces,
                    max_pieces=bread.fixed_pieces,
                )
            resolved.append(bread)
            continue
        own = bread.fixed_pieces is None
        resolved.append(
            replace(
                bread,
                group_id=None,
                group_name=None,
                min_pieces=(
                    bread.group_min_pieces
                    if own and bread.min_pieces is None
                    else bread.min_pieces
                ),
                max_pieces=(
                    bread.group_max_pieces
                    if own and bread.max_pieces is None
                    else bread.max_pieces
                ),
                group_min_pieces=None,
                group_max_pieces=None,
            )
        )
    return resolved


def group_min_pieces(members: list[BreadInfo]) -> int | None:
    """Every member's minimum bounds the group total, so the largest one counts."""
    return max(
        (b.group_min_pieces for b in members if b.group_min_pieces is not None),
        default=None,
    )


def group_max_pieces(members: list[BreadInfo]) -> int | None:
    """Every member's maximum bounds the group total, so the smallest one counts."""
    return min(
        (b.group_max_pieces for b in members if b.group_max_pieces is not None),
        default=None,
    )


def group_label(members: list[BreadInfo]) -> str:
    return members[0].group_name or ", ".join(b.name for b in members)
