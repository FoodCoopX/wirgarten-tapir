from ortools.sat.python import cp_model

from tapir.bakery.solver.dataclasses import BreadInfo, PickupLocationInfo


def build_model(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],
    max_sessions: int,
    stove_layers: int = 4,
    symmetry_breaking: bool = True,
    member_preferences: list[dict] | None = None,
) -> tuple[cp_model.CpModel, dict]:
    """
    Build the CP-SAT model and return (model, vars_dict).

    vars_dict contains all decision variables needed to extract solutions.

    member_preferences: optional list of dicts, each with:
        - member_id: int
        - location_id: int
        - preferred_bread_ids: list[int]   (1–3 bread IDs)
      Used to steer distribution so each member gets at least one preferred bread.
    """
    model = cp_model.CpModel()

    bread_map = {b.bread_id: b for b in available_breads}
    bread_ids = list(bread_map.keys())
    total_deliveries = sum(loc.total_deliveries for loc in pickup_locations)

    if member_preferences is None:
        member_preferences = []

    # -----------------------------------------------------------------------
    # Decision variables
    # -----------------------------------------------------------------------

    # 1. Stove layers: layer[sess, lay, b_id, qi] = 1 if bread b_id with
    #    quantity option qi is assigned to this layer
    layer = {}
    layer_used = {}
    session_used = {}
    for sess in range(max_sessions):
        session_used[sess] = model.new_bool_var(f"sess_used_{sess}")
        for lay in range(stove_layers):
            layer_used[sess, lay] = model.new_bool_var(f"layer_used_{sess}_{lay}")
            for b_id in bread_ids:
                bread = bread_map[b_id]
                if bread.fixed_pieces is not None:
                    continue  # fixed breads don't use the stove
                for qi in range(len(bread.pieces_per_stove_layer)):
                    layer[sess, lay, b_id, qi] = model.new_bool_var(
                        f"layer_{sess}_{lay}_{b_id}_{qi}"
                    )

    # 2. Total baked per bread type
    total_baked = {}
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            lb = bread.fixed_pieces
            ub = bread.fixed_pieces
        else:
            lb = bread.min_pieces if bread.min_pieces is not None else 0
            ub = (
                bread.max_pieces
                if bread.max_pieces is not None
                else total_deliveries * stove_layers
            )
        total_baked[b_id] = model.new_int_var(lb, ub, f"total_{b_id}")

    # 3. Whether each bread is baked at all
    bread_is_baked = {}
    for b_id in bread_ids:
        bread_is_baked[b_id] = model.new_bool_var(f"baked_{b_id}")

    # 4. Distribution per (bread, location)
    distribution_vars = {}
    for b_id in bread_ids:
        for loc in pickup_locations:
            fixed = loc.fixed_demand.get(b_id, 0)
            max_at_location = capacities.get((b_id, loc.location_id), 0)
            distribution_vars[b_id, loc.location_id] = model.new_int_var(
                fixed, max_at_location, f"dist_{b_id}_{loc.location_id}"
            )

    # 5. Remaining (waste) per bread
    remaining = {}
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            remaining[b_id] = model.new_int_var(0, 0, f"remaining_{b_id}")
        else:
            ub = (
                bread.max_pieces
                if bread.max_pieces is not None
                else total_deliveries * stove_layers
            )
            remaining[b_id] = model.new_int_var(0, ub, f"remaining_{b_id}")

    # 6. Track which sessions each bread appears in (only non-fixed breads)
    bread_in_session = {}
    sessions_per_bread = {}
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            continue
        sessions_per_bread[b_id] = model.new_int_var(
            0, max_sessions, f"sessions_for_{b_id}"
        )
        for sess in range(max_sessions):
            bread_in_session[b_id, sess] = model.new_bool_var(
                f"bread_{b_id}_in_sess_{sess}"
            )

    # 7. Variety tracking: how many distinct bread types at each location
    bread_at_location = {}
    variety_count = {}
    for loc in pickup_locations:
        variety_count[loc.location_id] = model.new_int_var(
            0, len(bread_ids), f"variety_{loc.location_id}"
        )
        for b_id in bread_ids:
            bread_at_location[b_id, loc.location_id] = model.new_bool_var(
                f"bread_at_loc_{b_id}_{loc.location_id}"
            )

    # 8. Member preference satisfaction
    #    For each member at a location: satisfied = 1 if at least one of their
    #    preferred breads is delivered to that location (distribution >= 1).
    #    A member with 3 preferred breads counts as 1 satisfied member (not 3).
    member_satisfied = {}
    valid_member_prefs = []
    for i, mp in enumerate(member_preferences):
        loc_id = mp["location_id"]
        # Filter to preferred breads that actually exist in this problem
        valid_breads = [b_id for b_id in mp["preferred_bread_ids"] if b_id in bread_map]
        if not valid_breads:
            continue
        if not any(loc.location_id == loc_id for loc in pickup_locations):
            continue

        member_satisfied[i] = model.new_bool_var(
            f"member_sat_{mp['member_id']}_{loc_id}"
        )
        valid_member_prefs.append((i, mp, valid_breads))

    # -----------------------------------------------------------------------
    # Constraints
    # -----------------------------------------------------------------------

    # C1: Each stove layer has at most one (bread, qty) assignment
    for sess in range(max_sessions):
        for lay in range(stove_layers):
            all_options = []
            for b_id in bread_ids:
                bread = bread_map[b_id]
                if bread.fixed_pieces is not None:
                    continue
                for qi in range(len(bread.pieces_per_stove_layer)):
                    all_options.append(layer[sess, lay, b_id, qi])
            model.add(sum(all_options) <= 1)
            model.add(layer_used[sess, lay] == sum(all_options))

    # C2: Session used iff any layer is used
    for sess in range(max_sessions):
        for lay in range(stove_layers):
            model.add(layer_used[sess, lay] <= session_used[sess])
        model.add(
            session_used[sess]
            <= sum(layer_used[sess, lay] for lay in range(stove_layers))
        )

    # C3: Layer packing — no gaps (layer N used => layer N-1 used)
    for sess in range(max_sessions):
        for lay in range(1, stove_layers):
            model.add(layer_used[sess, lay] <= layer_used[sess, lay - 1])

    # C4: Total baked = sum of all layer contributions (non-fixed breads only)
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            continue
        contributions = []
        for sess in range(max_sessions):
            for lay in range(stove_layers):
                for qi, qty in enumerate(bread.pieces_per_stove_layer):
                    contributions.append(qty * layer[sess, lay, b_id, qi])
        model.add(total_baked[b_id] == sum(contributions))

    # C5: Link bread_is_baked to total_baked
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            model.add(bread_is_baked[b_id] == 1)
            continue
        model.add(total_baked[b_id] >= 1).only_enforce_if(bread_is_baked[b_id])
        model.add(total_baked[b_id] == 0).only_enforce_if(
            bread_is_baked[b_id].negated()
        )

    # C6: Total baked = total distributed + remaining
    for b_id in bread_ids:
        bread = bread_map[b_id]
        total_distributed = sum(
            distribution_vars[b_id, loc.location_id] for loc in pickup_locations
        )
        model.add(total_baked[b_id] == total_distributed + remaining[b_id])
        if bread.fixed_pieces is None:
            model.add(remaining[b_id] >= bread.min_remaining_pieces).only_enforce_if(
                bread_is_baked[b_id]
            )

    # C7: Each location distributes exactly its total deliveries
    for loc in pickup_locations:
        model.add(
            sum(distribution_vars[b_id, loc.location_id] for b_id in bread_ids)
            == loc.total_deliveries
        )

    # C8: If a bread has fixed demand anywhere, it MUST be baked
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            continue
        total_fixed = sum(loc.fixed_demand.get(b_id, 0) for loc in pickup_locations)
        if total_fixed > 0:
            model.add(bread_is_baked[b_id] == 1)

    # C9: Track which sessions each bread appears in (non-fixed only)
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            continue
        for sess in range(max_sessions):
            has_bread_in_sess = []
            for lay in range(stove_layers):
                for qi in range(len(bread.pieces_per_stove_layer)):
                    has_bread_in_sess.append(layer[sess, lay, b_id, qi])
            model.add(sum(has_bread_in_sess) >= 1).only_enforce_if(
                bread_in_session[b_id, sess]
            )
            model.add(sum(has_bread_in_sess) == 0).only_enforce_if(
                bread_in_session[b_id, sess].negated()
            )
        model.add(
            sessions_per_bread[b_id]
            == sum(bread_in_session[b_id, sess] for sess in range(max_sessions))
        )

    # C10: Breads that can't span sessions: at most 1 session
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            continue
        if not bread.can_span_sessions:
            model.add(sessions_per_bread[b_id] <= 1)

    # C11: Breads that CAN span: hard limit to 2 sessions
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            continue
        if bread.can_span_sessions:
            model.add(sessions_per_bread[b_id] <= 2)

    # C12: Symmetry breaking — used sessions come first
    if symmetry_breaking:
        for sess in range(1, max_sessions):
            model.add(session_used[sess] <= session_used[sess - 1])

    # C13: Track variety at each location
    for loc in pickup_locations:
        for b_id in bread_ids:
            model.add(distribution_vars[b_id, loc.location_id] >= 1).only_enforce_if(
                bread_at_location[b_id, loc.location_id]
            )
            model.add(distribution_vars[b_id, loc.location_id] == 0).only_enforce_if(
                bread_at_location[b_id, loc.location_id].negated()
            )
        model.add(
            variety_count[loc.location_id]
            == sum(bread_at_location[b_id, loc.location_id] for b_id in bread_ids)
        )

    # C14: Member preference satisfaction
    #      A member is satisfied if at least one of their preferred breads
    #      is delivered to their location (i.e. distribution >= 1).
    #      This uses bread_at_location which is already linked to distribution.
    for i, mp, valid_breads in valid_member_prefs:
        loc_id = mp["location_id"]
        # member_satisfied[i] == 1  =>  at least one preferred bread at location
        # member_satisfied[i] == 0  =>  none of the preferred breads at location
        #
        # sum(bread_at_location[b, loc] for b in preferred) >= 1
        #   implies member can be satisfied.
        # We use: member_satisfied <= sum(bread_at_location[b, loc] for preferred)
        #         member_satisfied >= bread_at_location[b, loc] for each preferred b
        #   (the second is not needed — the optimizer will set it to 1 when possible)
        preferred_at_loc = [
            bread_at_location[b_id, loc_id]
            for b_id in valid_breads
            if (b_id, loc_id) in bread_at_location
        ]
        if not preferred_at_loc:
            model.add(member_satisfied[i] == 0)
            continue
        # Can only be satisfied if at least one preferred bread is there
        model.add(member_satisfied[i] <= sum(preferred_at_loc))
        # The optimizer will maximize this, so no need for a lower bound constraint

    # -----------------------------------------------------------------------
    # Objective — strict priority ordering via large weight gaps
    #
    # Priority (highest first):
    #   1. Minimize stove sessions
    #   2. Minimize session spanning
    #   3. Maximize member preference satisfaction (at least 1 preferred bread)
    #   4. Minimize waste
    #   5. Maximize variety at locations
    # -----------------------------------------------------------------------

    SESSIONS_W = 10_000_000
    SPANNING_W = 1_000_000
    PREFERENCE_W = 10_000
    WASTE_W = 100
    VARIETY_W = 10

    total_sessions = sum(session_used[sess] for sess in range(max_sessions))
    total_spanning = sum(
        sessions_per_bread[b_id]
        for b_id in bread_ids
        if bread_map[b_id].fixed_pieces is None
    )
    total_waste = sum(remaining[b_id] for b_id in bread_ids)
    total_variety = sum(variety_count[loc.location_id] for loc in pickup_locations)
    total_members_satisfied = sum(member_satisfied.values()) if member_satisfied else 0

    model.maximize(
        -SESSIONS_W * total_sessions
        - SPANNING_W * total_spanning
        + PREFERENCE_W * total_members_satisfied
        - WASTE_W * total_waste
        + VARIETY_W * total_variety
    )

    # -----------------------------------------------------------------------
    # Return model + all vars needed for extraction
    # -----------------------------------------------------------------------
    vars_dict = {
        "bread_map": bread_map,
        "bread_ids": bread_ids,
        "pickup_locations": pickup_locations,
        "total_deliveries": total_deliveries,
        "distribution_vars": distribution_vars,
        "layer": layer,
        "layer_used": layer_used,
        "session_used": session_used,
        "total_baked": total_baked,
        "remaining": remaining,
        "bread_is_baked": bread_is_baked,
        "sessions_per_bread": sessions_per_bread,
        "max_sessions": max_sessions,
        "stove_layers": stove_layers,
        "member_satisfied": member_satisfied,
        "valid_member_prefs": valid_member_prefs,
        "total_member_prefs": len(valid_member_prefs),
    }
    return model, vars_dict


def extract_solution(value_fn, v: dict) -> dict:
    """
    Extract a solution from solver using a value function.

    value_fn: either solver.value or callback.value
    v: vars_dict from build_model
    """
    bread_ids = v["bread_ids"]
    bread_map = v["bread_map"]
    pickup_locations = v["pickup_locations"]
    max_sessions = v["max_sessions"]
    stove_layers = v["stove_layers"]
    member_satisfied = v.get("member_satisfied", {})
    total_member_prefs = v.get("total_member_prefs", 0)

    bread_quantities = {b_id: value_fn(v["total_baked"][b_id]) for b_id in bread_ids}
    remaining_quantities = {b_id: value_fn(v["remaining"][b_id]) for b_id in bread_ids}

    stove_sessions = []
    for sess in range(max_sessions):
        if not value_fn(v["session_used"][sess]):
            continue
        session_layers = []
        for lay in range(stove_layers):
            if not value_fn(v["layer_used"][sess, lay]):
                session_layers.append(None)
                continue
            found = False
            for b_id in bread_ids:
                bread = bread_map[b_id]
                if bread.fixed_pieces is not None:
                    continue
                for qi, qty in enumerate(bread.pieces_per_stove_layer):
                    if value_fn(v["layer"][sess, lay, b_id, qi]):
                        session_layers.append((b_id, qty))
                        found = True
                        break
                if found:
                    break
            if not found:
                session_layers.append(None)
        stove_sessions.append(session_layers)

    distribution: dict[tuple[int, int], int] = {}
    for b_id in bread_ids:
        for loc in pickup_locations:
            count = value_fn(v["distribution_vars"][b_id, loc.location_id])
            if count > 0:
                distribution[(b_id, loc.location_id)] = count

    # Extract member preference satisfaction
    total_members_satisfied = sum(value_fn(var) for var in member_satisfied.values())

    return {
        "bread_quantities": bread_quantities,
        "remaining_quantities": remaining_quantities,
        "stove_sessions": stove_sessions,
        "distribution": distribution,
        "objective": 0,
        "members_satisfied": total_members_satisfied,
        "members_with_preferences": total_member_prefs,
    }
