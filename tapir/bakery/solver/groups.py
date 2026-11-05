from dataclasses import replace

from tapir.bakery.solver.dataclasses import BreadInfo


def stove_groups(breads: list[BreadInfo]) -> dict[str, list[BreadInfo]]:
    """
    The groups that have at least two breads in the oven on this baking day; a
    group with a single one behaves like an ungrouped bread. A fixed_pieces
    bread occupies no stove layers, so it is left out of its group as it is
    left out of the oven plan.
    """
    groups: dict[str, list[BreadInfo]] = {}
    for bread in breads:
        if bread.group_id is None or bread.fixed_pieces is not None:
            continue
        groups.setdefault(bread.group_id, []).append(bread)
    return {
        group_id: members for group_id, members in groups.items() if len(members) > 1
    }


def resolve_groups(breads: list[BreadInfo]) -> list[BreadInfo]:
    """
    Turns every bread that is not in a stove group on this day into an
    ungrouped one. Its group would only contain itself, so as for any ungrouped
    bread its settings for the day replace its own values. A fixed_pieces
    bread keeps no min/max: the fixed amount overrides them.
    """
    grouped_ids = {
        b.bread_id for members in stove_groups(breads).values() for b in members
    }
    resolved = []
    for bread in breads:
        if bread.bread_id in grouped_ids:
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
