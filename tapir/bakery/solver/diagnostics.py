from tapir.bakery.solver.dataclasses import (
    BreadInfo,
    PickupLocationInfo,
    SolverDiagnostic,
)


def diagnose_infeasibility(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],
    max_sessions: int,
    stove_layers: int,
) -> list[SolverDiagnostic]:
    diagnostics: list[SolverDiagnostic] = []

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

    # ── 0. Check for breads with empty pieces_per_stove_layer ────────
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

    # ── 1. Check min_pieces > max_pieces ─────────────────────────────
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
            elif b.min_pieces == b.max_pieces:
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

    # ── 2. Check fixed_demand vs capacity ────────────────────────────
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

    # ── 3. Total fixed demand per bread vs achievable quantity ───────
    total_fixed_demand: dict[int, int] = {}
    for loc in pickup_locations:
        for bread_id, demand in (loc.fixed_demand or {}).items():
            total_fixed_demand[bread_id] = total_fixed_demand.get(bread_id, 0) + demand

    for bread_id, demand in total_fixed_demand.items():
        b = bread_map.get(bread_id)
        if b is None:
            continue
        achievable = _get_achievable_quantities(b, max_sessions, stove_layers)
        if not achievable:
            continue
        max_achievable = max(achievable)
        if demand > max_achievable:
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="fixed_demand_exceeds_production",
                    bread_name=b.name,
                    location_name=None,
                    message=(
                        f"Direkte Brotwahl für '{b.name}' ergibt {demand} Stück, "
                        f"aber maximal {max_achievable} können gebacken werden "
                        f"(bei {max_sessions} Ofengängen à {stove_layers} Lagen)."
                    ),
                )
            )

    # ── 4. Check min_pieces achievable ───────────────────────────────
    for b in valid_breads:
        if b.fixed_pieces is not None:
            continue
        if b.min_pieces is None or b.min_pieces == 0:
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

    # ── 5. Stove capacity vs total demand ────────────────────────────
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
    total_min_required = sum(
        b.min_pieces or 0 for b in valid_breads if b.fixed_pieces is None
    ) + sum(b.fixed_pieces or 0 for b in valid_breads if b.fixed_pieces is not None)

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

    # ── 6. Total capacity across locations vs deliveries ─────────────
    for b in valid_breads:
        if b.fixed_pieces is not None:
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

    # ── 7. Total deliveries vs total capacity ────────────────────────
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

    # ── 8. Total deliveries vs max deliverable bread ─────────────────
    # Check if the sum of max deliverable breads can cover all deliveries
    total_max_deliverable = 0
    bread_max_details = []
    for b in valid_breads:
        if b.fixed_pieces is not None:
            max_baked = b.fixed_pieces
        elif b.max_pieces is not None:
            max_baked = b.max_pieces
        else:
            # Estimate max from stove capacity
            achievable = _get_achievable_quantities(b, max_sessions, stove_layers)
            max_baked = max(achievable) if achievable else 0

        remaining = b.min_remaining_pieces or 0
        max_deliverable = max(0, max_baked - remaining)
        total_max_deliverable += max_deliverable
        bread_max_details.append(
            f"'{b.name}': max gebacken={max_baked}, min Rest={remaining}, max lieferbar={max_deliverable}"
        )

    if total_deliveries > total_max_deliverable:
        detail_str = "\n  ".join(bread_max_details)
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
                    f"Lösungen: max_pieces erhöhen, min_remaining_pieces senken, "
                    f"oder Lieferungen reduzieren."
                ),
            )
        )

    # ── 9. Per-location: deliveries vs sum of capacities ─────────────
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

    # ── 10. Non-spanning breads: check max achievable in single session ──
    for b in valid_breads:
        if b.fixed_pieces is not None or b.can_span_sessions:
            continue
        if not b.pieces_per_stove_layer:
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


def _get_achievable_quantities(
    bread: BreadInfo, max_sessions: int, stove_layers: int
) -> set[int]:
    """
    Return the set of all achievable baked quantities for a bread,
    given the number of sessions and layers.
    """
    if not bread.pieces_per_stove_layer:
        return set()

    options = [0] + list(bread.pieces_per_stove_layer)
    total_layers = max_sessions * stove_layers

    achievable = {0}
    for _ in range(min(total_layers, 20)):
        new_achievable = set()
        for current in achievable:
            for opt in options:
                new_achievable.add(current + opt)
        achievable = new_achievable

    achievable.discard(0)
    return achievable
