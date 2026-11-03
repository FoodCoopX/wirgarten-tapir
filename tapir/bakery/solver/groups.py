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


def group_min_pieces(members: list[BreadInfo]) -> int | None:
    """Every member's min_pieces bounds the group total, so the largest one counts."""
    return max(
        (b.min_pieces for b in members if b.min_pieces is not None), default=None
    )


def group_max_pieces(members: list[BreadInfo]) -> int | None:
    """Every member's max_pieces bounds the group total, so the smallest one counts."""
    return min(
        (b.max_pieces for b in members if b.max_pieces is not None), default=None
    )


def group_label(members: list[BreadInfo]) -> str:
    return members[0].group_name or ", ".join(b.name for b in members)
