from ortools.sat.python import cp_model

from tapir.bakery.solver.dataclasses import BreadInfo, PickupLocationInfo
from tapir.bakery.solver.groups import (
    group_max_pieces,
    group_min_pieces,
    limit_groups,
    resolve_groups,
    stove_groups,
)


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
    member_preferences: dicts of member_id, location_id, preferred_bread_ids.
    """
    model = cp_model.CpModel()

    available_breads = resolve_groups(available_breads)
    bread_map = {b.bread_id: b for b in available_breads}
    bread_ids = list(bread_map.keys())
    total_deliveries = sum(loc.total_deliveries for loc in pickup_locations)

    if member_preferences is None:
        member_preferences = []

    # Stove units are what a layer is given to: a group, whose breads may
    # share the layer, or an ungrouped bread. Fixed breads don't use the stove.
    groups = stove_groups(available_breads)
    grouped_bread_ids = {b.bread_id for members in groups.values() for b in members}
    stove_units = [tuple(b.bread_id for b in members) for members in groups.values()]
    stove_units += [
        (b_id,)
        for b_id in bread_ids
        if bread_map[b_id].fixed_pieces is None and b_id not in grouped_bread_ids
    ]
    unit_options = [
        sorted({qty for b_id in unit for qty in bread_map[b_id].pieces_per_stove_layer})
        for unit in stove_units
    ]

    # 1. Stove layers: layer[sess, lay, u, qi] = 1 if stove unit u fills this
    #    layer with unit_options[u][qi] pieces
    layer = {}
    layer_used = {}
    session_used = {}
    for sess in range(max_sessions):
        session_used[sess] = model.new_bool_var(f"sess_used_{sess}")
        for lay in range(stove_layers):
            layer_used[sess, lay] = model.new_bool_var(f"layer_used_{sess}_{lay}")
            for u in range(len(stove_units)):
                for qi in range(len(unit_options[u])):
                    layer[sess, lay, u, qi] = model.new_bool_var(
                        f"layer_{sess}_{lay}_{u}_{qi}"
                    )

    # pieces[sess, lay, b_id]: how many of the layer's pieces are bread b_id;
    # on_layer[sess, lay, b_id]: whether there are any. For an ungrouped bread
    # both are just expressions over its layer options.
    pieces = {}
    on_layer = {}
    for sess in range(max_sessions):
        for lay in range(stove_layers):
            for u, unit in enumerate(stove_units):
                options = unit_options[u]
                unit_pieces = sum(
                    qty * layer[sess, lay, u, qi] for qi, qty in enumerate(options)
                )
                if len(unit) == 1:
                    (b_id,) = unit
                    pieces[sess, lay, b_id] = unit_pieces
                    on_layer[sess, lay, b_id] = sum(
                        layer[sess, lay, u, qi] for qi in range(len(options))
                    )
                    continue
                for b_id in unit:
                    bread_options = bread_map[b_id].pieces_per_stove_layer
                    pieces[sess, lay, b_id] = model.new_int_var(
                        0, max(bread_options), f"pieces_{sess}_{lay}_{b_id}"
                    )
                    on_layer[sess, lay, b_id] = model.new_bool_var(
                        f"on_layer_{sess}_{lay}_{b_id}"
                    )
                    model.add(pieces[sess, lay, b_id] >= 1).only_enforce_if(
                        on_layer[sess, lay, b_id]
                    )
                    model.add(pieces[sess, lay, b_id] == 0).only_enforce_if(
                        on_layer[sess, lay, b_id].negated()
                    )
                    # A shared layer holds a number of pieces every bread on it
                    # allows.
                    for qi, qty in enumerate(options):
                        if qty not in bread_options:
                            model.add_bool_or(
                                on_layer[sess, lay, b_id].negated(),
                                layer[sess, lay, u, qi].negated(),
                            )
                model.add(sum(pieces[sess, lay, b_id] for b_id in unit) == unit_pieces)

    total_baked = {}
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            lb = bread.fixed_pieces
            ub = bread.fixed_pieces
        else:
            # For a grouped bread these are its settings for the day; C15
            # bounds the group's total.
            lb = bread.min_pieces if bread.min_pieces is not None else 0
            ub = (
                bread.max_pieces
                if bread.max_pieces is not None
                else total_deliveries * stove_layers
            )
        total_baked[b_id] = model.new_int_var(lb, ub, f"total_{b_id}")

    bread_is_baked = {}
    for b_id in bread_ids:
        bread_is_baked[b_id] = model.new_bool_var(f"baked_{b_id}")

    distribution_vars = {}
    for b_id in bread_ids:
        for loc in pickup_locations:
            fixed = loc.fixed_demand.get(b_id, 0)
            max_at_location = capacities.get((b_id, loc.location_id), 0)
            distribution_vars[b_id, loc.location_id] = model.new_int_var(
                fixed, max_at_location, f"dist_{b_id}_{loc.location_id}"
            )

    remaining = {}
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.fixed_pieces is not None:
            # Pinning this to zero would force total_distributed ==
            # fixed_pieces exactly, which is infeasible unless the number
            # ordered happens to match the number baked.
            remaining[b_id] = model.new_int_var(
                0, bread.fixed_pieces, f"remaining_{b_id}"
            )
        else:
            ub = (
                bread.max_pieces
                if bread.max_pieces is not None
                else total_deliveries * stove_layers
            )
            remaining[b_id] = model.new_int_var(0, ub, f"remaining_{b_id}")

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

    # A member is satisfied when one loaf of a bread they prefer is set aside
    # for them; a member with three favourites counts once, not three times.
    member_satisfied = {}
    member_gets_bread = {}
    valid_member_prefs = []
    for i, mp in enumerate(member_preferences):
        loc_id = mp["location_id"]
        valid_breads = [
            b_id
            for b_id in mp["preferred_bread_ids"]
            if b_id in bread_map and (b_id, loc_id) in distribution_vars
        ]
        if not valid_breads:
            continue
        if not any(loc.location_id == loc_id for loc in pickup_locations):
            continue

        member_satisfied[i] = model.new_bool_var(
            f"member_sat_{mp['member_id']}_{loc_id}"
        )
        for b_id in valid_breads:
            member_gets_bread[i, b_id] = model.new_bool_var(f"member_{i}_gets_{b_id}")
        valid_member_prefs.append((i, mp, valid_breads))

    # C1: Each stove layer has at most one (stove unit, qty) assignment
    for sess in range(max_sessions):
        for lay in range(stove_layers):
            all_options = [
                layer[sess, lay, u, qi]
                for u in range(len(stove_units))
                for qi in range(len(unit_options[u]))
            ]
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
        model.add(
            total_baked[b_id]
            == sum(
                pieces[sess, lay, b_id]
                for sess in range(max_sessions)
                for lay in range(stove_layers)
            )
        )

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
            has_bread_in_sess = [
                on_layer[sess, lay, b_id] for lay in range(stove_layers)
            ]
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

    # C14: One loaf per satisfied member, the same rule
    #      PreferenceSatisfactionService applies when it simulates the pickup.
    for i, mp, valid_breads in valid_member_prefs:
        model.add(
            sum(member_gets_bread[i, b_id] for b_id in valid_breads)
            == member_satisfied[i]
        )

    # C14b: a bread cannot be claimed more often than it is distributed
    for loc in pickup_locations:
        for b_id in bread_ids:
            claims = [
                member_gets_bread[i, b_id]
                for i, mp, valid_breads in valid_member_prefs
                if mp["location_id"] == loc.location_id
                and (i, b_id) in member_gets_bread
            ]
            if claims:
                model.add(sum(claims) <= distribution_vars[b_id, loc.location_id])

    # C15: Every grouped bread's own min/max (not the day's) bounds its
    #      group's total, a fixed amount outside the oven included
    for members in limit_groups(available_breads).values():
        group_total = sum(total_baked[b.bread_id] for b in members)
        group_min = group_min_pieces(members)
        group_max = group_max_pieces(members)
        if group_min is not None:
            model.add(group_total >= group_min)
        if group_max is not None:
            model.add(group_total <= group_max)

    # Objective terms, by weight: fewest stove sessions, least session
    # spanning, most members getting a preferred bread, least waste, fewest
    # shared layers, most variety at the stations. The weights are exchange
    # rates, not a strict priority: one session is worth 1000 satisfied
    # members, one spanning bread 100 members, one member 100 loaves of waste,
    # and one loaf of waste 10 points of variety. Splitting a bread is intended
    # once it satisfies more than 100 additional members. A bread sharing a
    # layer costs less than a loaf of waste and more than variety at 5
    # stations: a group's layer is shared to save waste or to give members
    # their favourite, but variety alone only pays for it when the extra bread
    # reaches more than 5 stations, so the bakers don't get single-loaf splits.
    #
    # The spread is not part of it: _run_solver minimises it in a second solve
    # that keeps this objective at its best value, so it only chooses among
    # otherwise equal plans.

    SESSIONS_W = 10_000_000
    SPANNING_W = 1_000_000
    PREFERENCE_W = 10_000
    WASTE_W = 100
    SHARING_W = 55
    VARIETY_W = 10

    total_sessions = sum(session_used[sess] for sess in range(max_sessions))
    # Sessions beyond the first, which is what "spanning" means: the difference
    # is 0 for an unbaked or single-session bread and 1 for one spanning two.
    total_spanning = sum(
        sessions_per_bread[b_id] - bread_is_baked[b_id]
        for b_id in bread_ids
        if bread_map[b_id].fixed_pieces is None
    )
    total_waste = sum(remaining[b_id] for b_id in bread_ids)
    total_variety = sum(variety_count[loc.location_id] for loc in pickup_locations)
    total_members_satisfied = sum(member_satisfied.values()) if member_satisfied else 0
    # Breads beyond the first on a layer, which only a group's layer can have.
    # The group's own use of the layer, not layer_used: that is also 1 when
    # another unit holds the layer, and would turn the penalty into a reward.
    total_sharing = sum(
        sum(on_layer[sess, lay, b_id] for b_id in unit)
        - sum(layer[sess, lay, u, qi] for qi in range(len(unit_options[u])))
        for u, unit in enumerate(stove_units)
        if len(unit) > 1
        for sess in range(max_sessions)
        for lay in range(stove_layers)
    )
    # The spread: every station's count of every bread, squared. With a
    # station's total fixed it is smallest when its loaves are shared out
    # evenly, so middle counts win over 15 of one bread and 1 of the rest.
    # count² is the line through (k, k²) and (k + 1, (k + 1)²) for every k:
    # minimised, the square sits on the highest of them, which is count²
    # exactly at whole counts, and the LP relaxation stays tight.
    deliveries = {loc.location_id: loc.total_deliveries for loc in pickup_locations}
    squares = []
    for (b_id, loc_id), count in distribution_vars.items():
        # C7 caps a count at the station's deliveries, and a capacity can be
        # far larger.
        max_count = min(capacities.get((b_id, loc_id), 0), deliveries[loc_id])
        square = model.new_int_var(0, max_count * max_count, f"sq_{b_id}_{loc_id}")
        for k in range(max_count):
            model.add(square >= (2 * k + 1) * count - k * (k + 1))
        squares.append(square)
    total_spread = sum(squares)

    main_objective = (
        -SESSIONS_W * total_sessions
        - SPANNING_W * total_spanning
        + PREFERENCE_W * total_members_satisfied
        - WASTE_W * total_waste
        + VARIETY_W * total_variety
        - SHARING_W * total_sharing
    )
    model.maximize(main_objective)

    vars_dict = {
        "bread_map": bread_map,
        "bread_ids": bread_ids,
        "pickup_locations": pickup_locations,
        "total_deliveries": total_deliveries,
        "distribution_vars": distribution_vars,
        "pieces": pieces,
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
        "main_objective": main_objective,
        "spread": total_spread,
    }
    return model, vars_dict


def extract_solution(value_fn, v: dict) -> dict:
    """value_fn: either solver.value or callback.value."""
    bread_ids = v["bread_ids"]
    bread_map = v["bread_map"]
    pickup_locations = v["pickup_locations"]
    max_sessions = v["max_sessions"]
    stove_layers = v["stove_layers"]
    member_satisfied = v.get("member_satisfied", {})
    total_member_prefs = v.get("total_member_prefs", 0)

    bread_quantities = {b_id: value_fn(v["total_baked"][b_id]) for b_id in bread_ids}
    remaining_quantities = {b_id: value_fn(v["remaining"][b_id]) for b_id in bread_ids}

    stove_bread_ids = [
        b_id for b_id in bread_ids if bread_map[b_id].fixed_pieces is None
    ]
    stove_sessions = []
    for sess in range(max_sessions):
        if not value_fn(v["session_used"][sess]):
            continue
        session_layers = []
        for lay in range(stove_layers):
            breads_on_layer = []
            if value_fn(v["layer_used"][sess, lay]):
                for b_id in stove_bread_ids:
                    qty = value_fn(v["pieces"][sess, lay, b_id])
                    if qty > 0:
                        breads_on_layer.append((b_id, qty))
            session_layers.append(breads_on_layer)
        stove_sessions.append(session_layers)

    distribution: dict[tuple[int, int], int] = {}
    for b_id in bread_ids:
        for loc in pickup_locations:
            count = value_fn(v["distribution_vars"][b_id, loc.location_id])
            if count > 0:
                distribution[(b_id, loc.location_id)] = count

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
