from dataclasses import replace

from tapir.bakery.solver.dataclasses import (
    BreadInfo,
    PickupLocationInfo,
    SolverDiagnostic,
)
from tapir.bakery.solver.groups import (
    group_label,
    group_max_pieces,
    can_share_a_layer,
    group_min_pieces,
    limit_groups,
    resolve_groups,
)


def diagnose_infeasibility(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],
    max_sessions: int,
    stove_layers: int,
) -> list[SolverDiagnostic]:
    diagnostics: list[SolverDiagnostic] = []
    available_breads = resolve_groups(available_breads)

    if not available_breads:
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="no_breads",
                bread_name=None,
                location_name=None,
                message="Keine Brote für diesen Liefertag aktiviert.",
            )
        )
        return diagnostics

    if not pickup_locations:
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="no_locations",
                bread_name=None,
                location_name=None,
                message="Keine Abholstationen mit Lieferungen gefunden.",
            )
        )
        return diagnostics

    total_deliveries = sum(loc.total_deliveries for loc in pickup_locations)

    valid_breads = []
    for b in available_breads:
        if b.fixed_pieces is not None:
            valid_breads.append(b)
        elif not b.pieces_per_stove_layer:
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="configuration",
                    bread_name=b.name,
                    location_name=None,
                    message=(
                        f"Brot '{b.name}' hat keine Stückzahlen pro Ofenlage "
                        f"(pieces_per_stove_layer ist leer). "
                        f"Bitte in der Brotkonfiguration hinterlegen."
                    ),
                )
            )
        else:
            valid_breads.append(b)

    if not valid_breads:
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="no_valid_breads",
                bread_name=None,
                location_name=None,
                message="Kein Brot hat gültige Ofenlagen-Konfiguration.",
            )
        )
        return diagnostics

    bread_map = {b.bread_id: b for b in valid_breads}

    # A grouped bread's min_pieces/max_pieces are its settings for the day;
    # its group's limits come from group_min/max_pieces, see C15. A group
    # counts all its breads of the day, fixed amounts outside the oven too.
    groups = limit_groups(valid_breads)
    grouped_ids = {b.bread_id for members in groups.values() for b in members}
    group_of = {b.bread_id: members for members in groups.values() for b in members}

    def reach(bread: BreadInfo) -> int:
        """An upper bound on how much of the bread can be baked."""
        if bread.fixed_pieces is None and bread.bread_id in group_of:
            return _max_baked_in_group(
                bread, group_of[bread.bread_id], max_sessions, stove_layers
            )
        return _max_baked(bread, max_sessions, stove_layers)

    for b in valid_breads:
        if b.min_pieces is not None and b.max_pieces is not None:
            if b.min_pieces > b.max_pieces:
                diagnostics.append(
                    SolverDiagnostic(
                        level="error",
                        category="min_max_conflict",
                        bread_name=b.name,
                        location_name=None,
                        message=(
                            f"Brot '{b.name}': min_pieces ({b.min_pieces}) > "
                            f"max_pieces ({b.max_pieces}). Das ist widersprüchlich."
                        ),
                    )
                )
            # For a grouped bread a fixed amount would do just the same.
            elif b.min_pieces == b.max_pieces and b.bread_id not in grouped_ids:
                diagnostics.append(
                    SolverDiagnostic(
                        level="info",
                        category="min_max",
                        bread_name=b.name,
                        location_name=None,
                        message=(
                            f"Brot '{b.name}': min_pieces == max_pieces == {b.min_pieces}. "
                            f"Consider using fixed_pieces instead."
                        ),
                    )
                )

    for members in groups.values():
        label = group_label(members)
        group_min = group_min_pieces(members)
        group_max = group_max_pieces(members)
        if group_min is not None and group_max is not None and group_min > group_max:
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="group_min_max_conflict",
                    bread_name=None,
                    location_name=None,
                    message=(
                        f"Gruppe '{label}': zusammen mindestens {group_min} Stück "
                        f"(höchste Min.-Angabe), aber höchstens {group_max} Stück "
                        f"(niedrigste Max.-Angabe). Das ist widersprüchlich."
                    ),
                )
            )
        elif (
            len({b.group_min_pieces for b in members}) > 1
            or len({b.group_max_pieces for b in members}) > 1
        ):
            limits = [
                f"Min. {group_min}" if group_min is not None else None,
                f"Max. {group_max}" if group_max is not None else None,
            ]
            diagnostics.append(
                SolverDiagnostic(
                    level="info",
                    category="group_limits",
                    bread_name=None,
                    location_name=None,
                    message=(
                        f"Gruppe '{label}': die Brote haben unterschiedliche "
                        f"Min./Max.-Angaben, für die Summe der Gruppe gilt "
                        f"{' und '.join(limit for limit in limits if limit)} Stück."
                    ),
                )
            )

        # The day's settings of the group's breads, against the group.
        day_mins = sum(_day_min(b) for b in members)
        if group_max is not None and day_mins > group_max:
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="group_day_limits_conflict",
                    bread_name=None,
                    location_name=None,
                    message=(
                        f"Gruppe '{label}': die Tageseinstellungen verlangen "
                        f"zusammen mindestens {day_mins} Stück, die Gruppe darf "
                        f"aber höchstens {group_max} Stück backen."
                    ),
                )
            )
        if group_min and all(_day_max(b) is not None for b in members):
            day_maxes = sum(_day_max(b) for b in members)
            if day_maxes < group_min:
                diagnostics.append(
                    SolverDiagnostic(
                        level="error",
                        category="group_day_limits_conflict",
                        bread_name=None,
                        location_name=None,
                        message=(
                            f"Gruppe '{label}': die Tageseinstellungen erlauben "
                            f"zusammen höchstens {day_maxes} Stück, die Gruppe "
                            f"braucht aber mindestens {group_min} Stück."
                        ),
                    )
                )

    for b in valid_breads:
        if b.fixed_pieces is not None:
            continue
        members = group_of.get(b.bread_id)
        if members and _can_share_in_oven(b, members):
            # It can take part of a shared layer, so only what the group
            # leaves for the oven can keep it off every layer.
            max_pieces = _oven_room(members)
            limit = (
                f"die Gruppe '{group_label(members)}' darf im Ofen höchstens "
                f"{max_pieces} Stück backen, weniger"
            )
        elif members:
            max_pieces = _min_known(b.max_pieces, _oven_room(members))
            limit = (
                f"höchstens {max_pieces} Stück erlaubt, und es teilt mit keinem "
                f"anderen Brot der Gruppe eine Stückzahl pro Ofenlage; das ist weniger"
            )
        else:
            max_pieces = b.max_pieces
            limit = f"max_pieces={max_pieces} ist kleiner"
        if max_pieces is None:
            continue
        smallest_layer = min(b.pieces_per_stove_layer)
        if max_pieces < smallest_layer:
            diagnostics.append(
                SolverDiagnostic(
                    level="warning",
                    category="max_below_one_layer",
                    bread_name=b.name,
                    location_name=None,
                    message=(
                        f"Brot '{b.name}': {limit} als eine Ofenlage "
                        f"({smallest_layer} Stück), es kann nie gebacken werden."
                    ),
                )
            )

    for loc in pickup_locations:
        if not loc.fixed_demand:
            continue
        for bread_id, demand in loc.fixed_demand.items():
            cap = capacities.get((bread_id, loc.location_id), 0)
            bread_obj = bread_map.get(bread_id, None)
            bname = bread_obj.name if bread_obj else f"ID={bread_id}"

            if demand > cap:
                diagnostics.append(
                    SolverDiagnostic(
                        level="error",
                        category="fixed_demand_exceeds_capacity",
                        bread_name=bname,
                        location_name=loc.name,
                        message=(
                            f"'{loc.name}': {demand}× '{bname}' direkt gewählt, "
                            f"aber Kapazität ist nur {cap}."
                        ),
                    )
                )

            if bread_id not in bread_map:
                diagnostics.append(
                    SolverDiagnostic(
                        level="warning",
                        category="fixed_demand_unavailable",
                        bread_name=bname,
                        location_name=loc.name,
                        message=(
                            f"'{loc.name}': {demand}× '{bname}' direkt gewählt, "
                            f"aber dieses Brot ist nicht für diesen Tag aktiviert."
                        ),
                    )
                )

    total_fixed_demand: dict[int, int] = {}
    for loc in pickup_locations:
        for bread_id, demand in (loc.fixed_demand or {}).items():
            total_fixed_demand[bread_id] = total_fixed_demand.get(bread_id, 0) + demand

    for bread_id, demand in total_fixed_demand.items():
        b = bread_map.get(bread_id)
        if b is None:
            continue
        max_baked = reach(b)
        remaining = b.min_remaining_pieces or 0
        max_deliverable = max(0, max_baked - remaining)
        if demand > max_deliverable:
            kept_back = f", davon mindestens {remaining} als Rest" if remaining else ""
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="fixed_demand_exceeds_production",
                    bread_name=b.name,
                    location_name=None,
                    message=(
                        f"Direkte Brotwahl für '{b.name}' ergibt {demand} Stück, "
                        f"aber maximal {max_deliverable} sind lieferbar "
                        f"(max. {max_baked} gebacken{kept_back})."
                    ),
                )
            )

    # The per-bread check above caps each bread at the group's max_pieces,
    # but the group's breads have to fit under it together, in whole layers.
    for members in groups.values():
        chosen = [b for b in members if total_fixed_demand.get(b.bread_id)]
        if not chosen:
            continue
        demand = sum(total_fixed_demand[b.bread_id] for b in chosen)
        # A chosen bread is baked, so it also keeps its minimum behind.
        remaining = sum(b.min_remaining_pieces or 0 for b in chosen)
        ceiling = _group_max_baked(members, max_sessions, stove_layers)
        if demand + remaining > ceiling:
            kept_back = f" plus mindestens {remaining} als Rest" if remaining else ""
            group_max = group_max_pieces(members)
            limit = (
                f" (Max. {group_max})"
                if group_max is not None and ceiling < group_max
                else ""
            )
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="fixed_demand_exceeds_production",
                    bread_name=None,
                    location_name=None,
                    message=(
                        f"Direkte Brotwahl für Gruppe '{group_label(members)}' "
                        f"ergibt zusammen {demand} Stück{kept_back}, aber die "
                        f"Gruppe kann in ganzen Ofenlagen höchstens {ceiling} "
                        f"Stück backen{limit}."
                    ),
                )
            )

    for members in groups.values():
        group_min = group_min_pieces(members) or 0
        group_max = group_max_pieces(members)
        day_mins = sum(_day_min(b) for b in members)
        required = max(group_min, day_mins)
        # Above the maximum, or a minimum above what the day's settings
        # allow, is already reported above.
        if not required or (group_max is not None and required > group_max):
            continue
        if all(_day_max(b) is not None for b in members) and (
            sum(_day_max(b) for b in members) < group_min
        ):
            continue
        ceiling = _group_max_baked(members, max_sessions, stove_layers)
        if required > ceiling:
            source = " nach den Tageseinstellungen" if day_mins > group_min else ""
            limit = f", Max. {group_max}" if group_max is not None else ""
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="min_not_achievable",
                    bread_name=None,
                    location_name=None,
                    message=(
                        f"Gruppe '{group_label(members)}': zusammen mindestens "
                        f"{required} Stück{source}, aber in ganzen Ofenlagen sind "
                        f"höchstens {ceiling} Stück erreichbar ({max_sessions} "
                        f"Ofengänge à {stove_layers} Lagen{limit})."
                    ),
                )
            )

    for b in valid_breads:
        if b.fixed_pieces is not None or not b.min_pieces:
            continue
        if b.bread_id in grouped_ids:
            members = group_of[b.bread_id]
            if b.min_pieces > reach(b):
                alone = (
                    ""
                    if _can_share_in_oven(b, members)
                    else " (es teilt mit keinem anderen Brot der Gruppe eine "
                    "Stückzahl pro Ofenlage)"
                )
                diagnostics.append(
                    SolverDiagnostic(
                        level="error",
                        category="min_not_achievable",
                        bread_name=b.name,
                        location_name=None,
                        message=(
                            f"Brot '{b.name}': Tageseinstellung Min. {b.min_pieces}, "
                            f"aber in der Gruppe '{group_label(members)}' sind "
                            f"höchstens {reach(b)} Stück erreichbar{alone}."
                        ),
                    )
                )
            continue
        achievable = _get_achievable_quantities(b, max_sessions, stove_layers)
        if not achievable:
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="min_not_achievable",
                    bread_name=b.name,
                    location_name=None,
                    message=(
                        f"Brot '{b.name}': min_pieces={b.min_pieces}, aber keine "
                        f"Stückzahl ist mit den Ofenlagen erreichbar."
                    ),
                )
            )
            continue
        if b.min_pieces > max(achievable):
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="min_not_achievable",
                    bread_name=b.name,
                    location_name=None,
                    message=(
                        f"Brot '{b.name}': min_pieces={b.min_pieces}, aber max. "
                        f"erreichbar sind {max(achievable)} Stück "
                        f"(bei {max_sessions} Ofengängen à {stove_layers} Lagen)."
                    ),
                )
            )
        valid_at_or_above_min = [q for q in achievable if q >= b.min_pieces]
        if not valid_at_or_above_min:
            diagnostics.append(
                SolverDiagnostic(
                    level="warning",
                    category="min_gap",
                    bread_name=b.name,
                    location_name=None,
                    message=(
                        f"Brot '{b.name}': min_pieces={b.min_pieces}, aber die "
                        f"nächst-erreichbaren Mengen sind {sorted(achievable)}. "
                        f"Keine davon ist ≥ {b.min_pieces}."
                    ),
                )
            )

    max_stove_capacity = (
        max_sessions
        * stove_layers
        * max(
            (
                max(b.pieces_per_stove_layer)
                for b in valid_breads
                if b.pieces_per_stove_layer
            ),
            default=0,
        )
    )
    total_min_required = (
        sum(
            b.min_pieces or 0
            for b in valid_breads
            if b.fixed_pieces is None and b.bread_id not in grouped_ids
        )
        # What a group needs in the oven; its fixed amounts are in the last sum.
        + sum(
            max(
                (group_min_pieces(members) or 0)
                - sum(b.fixed_pieces or 0 for b in members),
                sum(b.min_pieces or 0 for b in members if b.fixed_pieces is None),
                0,
            )
            for members in groups.values()
        )
        + sum(b.fixed_pieces or 0 for b in valid_breads if b.fixed_pieces is not None)
    )

    if total_min_required > 0 and max_stove_capacity > 0:
        if total_min_required > max_stove_capacity:
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="stove_overflow",
                    bread_name=None,
                    location_name=None,
                    message=(
                        f"Mindest-Gesamtproduktion ({total_min_required} Stück) "
                        f"übersteigt die Ofenkapazität ({max_stove_capacity} Stück "
                        f"bei {max_sessions} Ofengängen à {stove_layers} Lagen)."
                    ),
                )
            )

    for b in valid_breads:
        if b.fixed_pieces is not None or b.bread_id in grouped_ids:
            continue
        total_cap = sum(
            capacities.get((b.bread_id, loc.location_id), 0) for loc in pickup_locations
        )
        fixed = total_fixed_demand.get(b.bread_id, 0)
        if b.min_pieces is not None and b.min_pieces > 0:
            min_to_deliver = b.min_pieces - (b.min_remaining_pieces or 0)
            if min_to_deliver > total_cap:
                diagnostics.append(
                    SolverDiagnostic(
                        level="error",
                        category="capacity_too_low",
                        bread_name=b.name,
                        location_name=None,
                        message=(
                            f"Brot '{b.name}': min. {min_to_deliver} zu verteilen "
                            f"(min_pieces={b.min_pieces}, min_remaining={b.min_remaining_pieces or 0}), "
                            f"aber Gesamtkapazität an allen Stationen ist nur {total_cap}."
                        ),
                    )
                )

    total_capacity_all = sum(capacities.values())
    if total_deliveries > total_capacity_all:
        diagnostics.append(
            SolverDiagnostic(
                level="warning",
                category="total_capacity",
                bread_name=None,
                location_name=None,
                message=(
                    f"Gesamt-Lieferungen ({total_deliveries}) übersteigen die "
                    f"Gesamt-Kapazität aller Brot/Standort-Kombinationen ({total_capacity_all})."
                ),
            )
        )

    total_max_deliverable = 0
    bread_max_details = []
    splitting_would_help = False
    # A group counts once: together its breads stay within its max_pieces.
    units = [[b] for b in valid_breads if b.bread_id not in grouped_ids]
    units += groups.values()
    for members in units:
        max_baked = 0
        for b in members:
            bread_max_baked = reach(b)
            max_baked += bread_max_baked
            if (
                b.fixed_pieces is None
                and not b.can_span_sessions
                and reach(replace(b, can_span_sessions=True)) > bread_max_baked
            ):
                splitting_would_help = True

        if len(members) > 1:
            max_baked = min(
                max_baked, _group_max_baked(members, max_sessions, stove_layers)
            )
            # Something baked leaves at least the smallest minimum behind.
            remaining = min(b.min_remaining_pieces or 0 for b in members)
            name = f"Gruppe '{group_label(members)}'"
        else:
            remaining = members[0].min_remaining_pieces or 0
            name = f"'{members[0].name}'"
        max_deliverable = max(0, max_baked - remaining)
        total_max_deliverable += max_deliverable
        bread_max_details.append(
            f"{name}: max gebacken={max_baked}, min Rest={remaining}, max lieferbar={max_deliverable}"
        )

    if total_deliveries > total_max_deliverable:
        detail_str = "\n  ".join(bread_max_details)
        remedies = ["max_pieces erhöhen", "min_remaining_pieces senken"]
        if splitting_would_help:
            remedies.append("Backen über mehrere Ofengänge erlauben")
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="deliveries_exceed_production",
                bread_name=None,
                location_name=None,
                message=(
                    f"Nicht genug Brot für alle Lieferungen! "
                    f"{total_deliveries} Lieferungen, aber maximal {total_max_deliverable} Brote lieferbar.\n"
                    f"  {detail_str}\n"
                    f"Lösungen: {', '.join(remedies)} oder Lieferungen reduzieren."
                ),
            )
        )

    for loc in pickup_locations:
        loc_total_cap = sum(
            capacities.get((b.bread_id, loc.location_id), 0) for b in valid_breads
        )
        if loc.total_deliveries > loc_total_cap:
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="location_capacity",
                    bread_name=None,
                    location_name=loc.name,
                    message=(
                        f"Station '{loc.name}': {loc.total_deliveries} Lieferungen, "
                        f"aber Gesamtkapazität aller Brote dort ist nur {loc_total_cap}."
                    ),
                )
            )

    for b in valid_breads:
        if b.fixed_pieces is not None or b.can_span_sessions:
            continue
        if not b.pieces_per_stove_layer or b.bread_id in grouped_ids:
            continue
        max_per_session = stove_layers * max(b.pieces_per_stove_layer)
        if b.min_pieces is not None and b.min_pieces > max_per_session:
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="single_session_overflow",
                    bread_name=b.name,
                    location_name=None,
                    message=(
                        f"Brot '{b.name}' darf nicht über mehrere Ofengänge verteilt werden, "
                        f"aber min_pieces={b.min_pieces} > max pro Ofengang={max_per_session} "
                        f"({stove_layers} Lagen × {max(b.pieces_per_stove_layer)} Stück)."
                    ),
                )
            )

    return diagnostics


def _max_baked(bread: BreadInfo, max_sessions: int, stove_layers: int) -> int:
    if bread.fixed_pieces is not None:
        return bread.fixed_pieces
    achievable = _get_achievable_quantities(bread, max_sessions, stove_layers)
    if bread.max_pieces is not None:
        achievable = {q for q in achievable if q <= bread.max_pieces}
    return max(achievable, default=0)


def _day_min(bread: BreadInfo) -> int:
    """What the day's settings ask of a bread at least, a fixed amount too."""
    if bread.fixed_pieces is not None:
        return bread.fixed_pieces
    return bread.min_pieces or 0


def _day_max(bread: BreadInfo) -> int | None:
    if bread.fixed_pieces is not None:
        return bread.fixed_pieces
    return bread.max_pieces


def _min_known(*values: int | None) -> int | None:
    known = [value for value in values if value is not None]
    return min(known) if known else None


def _oven_room(members: list[BreadInfo]) -> int | None:
    """What the group's maximum leaves for its breads in the oven."""
    group_max = group_max_pieces(members)
    if group_max is None:
        return None
    return group_max - sum(b.fixed_pieces or 0 for b in members)


def _can_share_in_oven(bread: BreadInfo, members: list[BreadInfo]) -> bool:
    return can_share_a_layer(bread, [b for b in members if b.fixed_pieces is None])


def _max_baked_in_group(
    bread: BreadInfo,
    members: list[BreadInfo],
    max_sessions: int,
    stove_layers: int,
) -> int:
    """
    An upper bound for a grouped bread in the oven, within its setting for the
    day and what the group leaves for the oven. On a layer shared with another
    bread of the group it can take any part of a count it allows; otherwise
    only whole layers of its own counts.
    """
    room = _oven_room(members)
    if _can_share_in_oven(bread, members):
        reach = _max_baked(replace(bread, max_pieces=room), max_sessions, stove_layers)
        return _min_known(reach, bread.max_pieces)
    return _max_baked(
        replace(bread, max_pieces=_min_known(bread.max_pieces, room)),
        max_sessions,
        stove_layers,
    )


def _group_max_baked(
    members: list[BreadInfo], max_sessions: int, stove_layers: int
) -> int:
    """
    An upper bound on what a group bakes: its fixed amounts outside the oven,
    plus what its other breads reach in whole layers within the rest of its
    maximum. Every layer may take any count one of them allows, which
    overestimates, so a total above this is unreachable for certain.
    """
    fixed = sum(b.fixed_pieces or 0 for b in members)
    oven = [b for b in members if b.fixed_pieces is None]
    if not oven:
        return fixed
    room = _oven_room(members)
    # C10/C11 per bread: the group's breads together occupy at most this many.
    sessions = min(max_sessions, sum(2 if b.can_span_sessions else 1 for b in oven))
    options = {qty for b in oven for qty in b.pieces_per_stove_layer}
    by_bread = sum(
        _max_baked_in_group(b, members, max_sessions, stove_layers) for b in oven
    )
    # The oven part is a sum of whole layers, within both bounds.
    cap = _min_known(room, by_bread)
    reachable = _layer_sums(options, sessions * stove_layers)
    return fixed + max((q for q in reachable if q <= cap), default=0)


def _get_achievable_quantities(
    bread: BreadInfo, max_sessions: int, stove_layers: int
) -> set[int]:
    if not bread.pieces_per_stove_layer:
        return set()

    # C10 caps a non-spanning bread at one session, C11 a spanning one at two.
    sessions_for_bread = min(max_sessions, 2 if bread.can_span_sessions else 1)
    return _layer_sums(bread.pieces_per_stove_layer, sessions_for_bread * stove_layers)


def _layer_sums(options, total_layers: int) -> set[int]:
    """The totals that up to total_layers layers, each holding one of options, add up to."""
    options = [0] + list(options)
    achievable = {0}
    for _ in range(total_layers):
        new_achievable = set()
        for current in achievable:
            for opt in options:
                new_achievable.add(current + opt)
        achievable = new_achievable

    achievable.discard(0)
    return achievable
