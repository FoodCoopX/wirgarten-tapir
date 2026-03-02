"""
Bread Baking Optimizer
======================
Solves the weekly bread planning problem:
- How many of each bread to bake (respecting stove layer constraints)
- How to distribute breads across pickup locations (respecting capacities)
- Individual member deliveries with chosen breads are treated as fixed constraints

Uses OR-Tools CP-SAT solver for constraint programming.

Dependencies:
    pip install ortools
"""

from dataclasses import dataclass

from ortools.sat.python import cp_model

# ---------------------------------------------------------------------------
# Data classes for clean input/output
# ---------------------------------------------------------------------------


@dataclass
class BreadInfo:
    bread_id: int
    name: str
    pieces_per_stove_layer: list[int]  # e.g. [10, 11, 12]
    can_span_sessions: bool  # one_batch_can_be_baked_in_more_than_one_stove
    min_pieces: int | None  # minimum total pieces to bake (None = no minimum)
    max_pieces: int | None  # maximum total pieces to bake (None = no maximum)
    min_remaining_pieces: int  # minimum extra pieces beyond deliveries


@dataclass
class PickupLocationInfo:
    location_id: int
    name: str
    total_deliveries: int  # Total number of delivery slots at this location
    # Fixed demand: bread_id -> count (from members who chose specific breads)
    fixed_demand: dict[int, int]


@dataclass
class BakingPlanResult:
    """Output of the optimizer."""

    bread_quantities: dict[int, int]  # bread_id -> total quantity
    remaining_quantities: dict[int, int]  # bread_id -> remaining quantity
    stove_sessions: list[list[tuple[int, int] | None]]  # sessions x 4 layers
    distribution: dict[tuple[int, int], int]  # (bread_id, location_id) -> count
    total_deliveries: int
    sessions_used: int


# ---------------------------------------------------------------------------
# Solution collector for enumerating multiple solutions
# ---------------------------------------------------------------------------


# ...existing code...
class BreadSolutionCollector(cp_model.CpSolverSolutionCallback):
    def __init__(self, max_solutions, extract_fn):
        super().__init__()
        self._max_solutions = max_solutions
        self._extract_fn = extract_fn
        self._solutions = []

    def on_solution_callback(self):
        solution = self._extract_fn(self)
        solution["_objective"] = self.ObjectiveValue()
        self._solutions.append(solution)
        # Keep memory bounded
        if len(self._solutions) > self._max_solutions * 3:
            self._solutions.sort(key=lambda s: s["_objective"], reverse=True)
            self._solutions = self._solutions[: self._max_solutions]

    def get_best_solutions(self):
        """Return the N best DISTINCT solutions sorted by objective (descending).

        Only includes solutions within 5% of the best objective to filter out
        the poor intermediate solutions the solver finds early on.
        """
        if not self._solutions:
            return []

        self._solutions.sort(key=lambda s: s["_objective"], reverse=True)
        best_obj = self._solutions[0]["_objective"]

        # Filter: only keep solutions close to optimal
        # Since objectives are negative (minimizing costs), "close" means
        # not much worse (more negative)
        if best_obj < 0:
            threshold = best_obj * 1.05  # allow 5% worse
        else:
            threshold = best_obj * 0.95

        good = []
        seen_fingerprints = set()
        for sol in self._solutions:
            if sol["_objective"] < threshold:
                continue

            # Deduplicate by session structure
            fp = _solution_fingerprint(sol)
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)

            good.append(sol)
            if len(good) >= self._max_solutions:
                break

        return good

    @property
    def solutions(self) -> list[dict]:
        return self._solutions


def _solution_fingerprint(sol: dict) -> str:
    """Create a fingerprint to detect duplicate solutions."""
    parts = []
    for sess in sol.get("stove_sessions", []):
        layer_parts = []
        for layer_info in sess:
            if layer_info is None:
                layer_parts.append("_")
            else:
                b_id, qty = layer_info
                layer_parts.append(f"{b_id}:{qty}")
        parts.append("|".join(layer_parts))
    return "||".join(sorted(parts))


# ...existing code...
# ---------------------------------------------------------------------------
# Model builder — single source of truth for variables + constraints
# ---------------------------------------------------------------------------


def _build_model(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],
    max_sessions: int,
    symmetry_breaking: bool = True,
) -> tuple[cp_model.CpModel, dict]:
    """
    Build the CP-SAT model and return (model, vars_dict).

    vars_dict contains all decision variables needed to extract solutions.
    """
    model = cp_model.CpModel()

    bread_map = {b.bread_id: b for b in available_breads}
    bread_ids = list(bread_map.keys())
    total_deliveries = sum(loc.total_deliveries for loc in pickup_locations)

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
        for lay in range(4):
            layer_used[sess, lay] = model.new_bool_var(f"layer_used_{sess}_{lay}")
            for b_id in bread_ids:
                bread = bread_map[b_id]
                for qi in range(len(bread.pieces_per_stove_layer)):
                    layer[sess, lay, b_id, qi] = model.new_bool_var(
                        f"layer_{sess}_{lay}_{b_id}_{qi}"
                    )

    # 2. Total baked per bread type
    total_baked = {}
    for b_id in bread_ids:
        bread = bread_map[b_id]
        lb = bread.min_pieces if bread.min_pieces is not None else 0
        ub = bread.max_pieces if bread.max_pieces is not None else total_deliveries * 4
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
        ub = bread.max_pieces if bread.max_pieces is not None else total_deliveries * 4
        remaining[b_id] = model.new_int_var(0, ub, f"remaining_{b_id}")

    # 6. Track which sessions each bread appears in
    bread_in_session = {}
    sessions_per_bread = {}
    for b_id in bread_ids:
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

    # -----------------------------------------------------------------------
    # Constraints
    # -----------------------------------------------------------------------

    # C1: Each stove layer has at most one (bread, qty) assignment
    for sess in range(max_sessions):
        for lay in range(4):
            all_options = []
            for b_id in bread_ids:
                bread = bread_map[b_id]
                for qi in range(len(bread.pieces_per_stove_layer)):
                    all_options.append(layer[sess, lay, b_id, qi])
            model.add(sum(all_options) <= 1)
            # Link layer_used
            model.add(layer_used[sess, lay] == sum(all_options))

    # C2: Session used iff any layer is used
    for sess in range(max_sessions):
        for lay in range(4):
            model.add(layer_used[sess, lay] <= session_used[sess])
        model.add(session_used[sess] <= sum(layer_used[sess, lay] for lay in range(4)))

    # C3: Layer packing — no gaps (layer N used => layer N-1 used)
    for sess in range(max_sessions):
        for lay in range(1, 4):
            model.add(layer_used[sess, lay] <= layer_used[sess, lay - 1])

    # C4: Total baked = sum of all layer contributions
    for b_id in bread_ids:
        bread = bread_map[b_id]
        contributions = []
        for sess in range(max_sessions):
            for lay in range(4):
                for qi, qty in enumerate(bread.pieces_per_stove_layer):
                    contributions.append(qty * layer[sess, lay, b_id, qi])
        model.add(total_baked[b_id] == sum(contributions))

    # C5: Link bread_is_baked to total_baked
    for b_id in bread_ids:
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
        # Minimum remaining when baked
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
        total_fixed = sum(loc.fixed_demand.get(b_id, 0) for loc in pickup_locations)
        if total_fixed > 0:
            model.add(bread_is_baked[b_id] == 1)

    # C9: Track which sessions each bread appears in
    for b_id in bread_ids:
        bread = bread_map[b_id]
        for sess in range(max_sessions):
            has_bread_in_sess = []
            for lay in range(4):
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

    # C10: HARD constraint — breads that can't span sessions: at most 1 session
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if not bread.can_span_sessions:
            model.add(sessions_per_bread[b_id] <= 1)

    # C11: Even breads that CAN span — prefer fewer sessions (SOFT, via objective)
    #      but HARD limit to at most 2 sessions to keep things sane
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.can_span_sessions:
            model.add(sessions_per_bread[b_id] <= 2)

    # C12: Symmetry breaking — used sessions come first
    if symmetry_breaking:
        for sess in range(1, max_sessions):
            model.add(session_used[sess] <= session_used[sess - 1])

    # C13: Track variety at each location
    for loc in pickup_locations:
        for b_id in bread_ids:
            # bread_at_location = 1 iff distribution > 0
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

        # -----------------------------------------------------------------------
        # Objective — strict priority ordering
        # -----------------------------------------------------------------------
        # Priority 1 (highest): Minimize sessions
        # Priority 2: Minimize total waste (remaining)
        # Priority 3: Maximize variety at each location
        #
        # We use large weight gaps to enforce lexicographic priority.

    SESSIONS_W = 1_000_000
    SPANNING_W = 100_000
    WASTE_W = 1_000
    VARIETY_W = 100

    total_sessions = sum(session_used[sess] for sess in range(max_sessions))
    total_spanning = sum(sessions_per_bread[b_id] for b_id in bread_ids)
    total_waste = sum(remaining[b_id] for b_id in bread_ids)
    total_variety = sum(variety_count[loc.location_id] for loc in pickup_locations)

    model.maximize(
        -SESSIONS_W * total_sessions
        - SPANNING_W * total_spanning
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
    }
    return model, vars_dict


def _extract_solution(value_fn, v: dict) -> dict:
    """
    Extract a solution from solver using a value function.

    value_fn: either solver.value or callback.value
    v: vars_dict from _build_model
    """
    bread_ids = v["bread_ids"]
    bread_map = v["bread_map"]
    pickup_locations = v["pickup_locations"]
    max_sessions = v["max_sessions"]

    bread_quantities = {b_id: value_fn(v["total_baked"][b_id]) for b_id in bread_ids}
    remaining_quantities = {b_id: value_fn(v["remaining"][b_id]) for b_id in bread_ids}

    stove_sessions = []
    for sess in range(max_sessions):
        if not value_fn(v["session_used"][sess]):
            continue
        session_layers = []
        for lay in range(4):
            if not value_fn(v["layer_used"][sess, lay]):
                session_layers.append(None)
                continue
            found = False
            for b_id in bread_ids:
                bread = bread_map[b_id]
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

    return {
        "bread_quantities": bread_quantities,
        "remaining_quantities": remaining_quantities,
        "stove_sessions": stove_sessions,
        "distribution": distribution,
        "objective": 0,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def solve_bread_planning(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],
    max_sessions: int = 10,
    time_limit_seconds: int = 60,
    max_solutions: int = 1,
    solution_index: int = 0,
) -> BakingPlanResult | None:
    """
    Solve the weekly bread planning problem.

    Returns BakingPlanResult or None if infeasible.
    """
    if not available_breads or not pickup_locations:
        return None

    for b in available_breads:
        if not b.pieces_per_stove_layer:
            print(f"⚠️  Bread {b.name} has EMPTY pieces_per_stove_layer!")
            return None

    total_deliveries = sum(loc.total_deliveries for loc in pickup_locations)

    print("=" * 80)
    print("SOLVER INPUT DEBUG")
    print("=" * 80)
    print(f"Available breads: {len(available_breads)}")
    for b in available_breads:
        print(f"  - {b.name} (id={b.bread_id})")
        print(f"    pieces_per_layer: {b.pieces_per_stove_layer}")
        print(f"    can_span_sessions: {b.can_span_sessions}")
        print(f"    min/max: {b.min_pieces}/{b.max_pieces}")
        print(f"    min_remaining: {b.min_remaining_pieces}")
    print(f"\nPickup locations: {len(pickup_locations)}")
    for loc in pickup_locations:
        print(
            f"  - {loc.name} (id={loc.location_id}): {loc.total_deliveries} deliveries"
        )
        if loc.fixed_demand:
            print(f"    Fixed demand: {loc.fixed_demand}")
    print(f"\nTotal deliveries: {total_deliveries}")

    use_symmetry = max_solutions <= 1
    model, v = _build_model(
        available_breads, pickup_locations, capacities, max_sessions, use_symmetry
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_workers = 8
    solver.parameters.log_search_progress = True

    if max_solutions > 1:
        solver.parameters.enumerate_all_solutions = False

        def make_extractor(vd):
            def extract(callback):
                sol = _extract_solution(callback.value, vd)
                sol["objective"] = callback.objective_value
                return sol

            return extract

        collector = BreadSolutionCollector(max_solutions, make_extractor(v))
        status = solver.solve(model, collector)

        print(f"\nSolver status: {solver.status_name(status)}")
        print(f"Raw solutions found: {len(collector.solutions)}")

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        if not collector.solutions:
            return None

        sorted_solutions = collector.get_best_solutions()
        print(f"Good distinct solutions: {len(sorted_solutions)}")
        for i, s in enumerate(sorted_solutions):
            print(f"  Solution {i}: objective={s['_objective']}")

        if not sorted_solutions:
            return None

        idx = min(solution_index, len(sorted_solutions) - 1)
        chosen = sorted_solutions[idx]
    else:
        status = solver.solve(model)
        print(f"\nSolver status: {solver.status_name(status)}")
        print(f"Objective: {solver.objective_value}")

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None

        chosen = _extract_solution(solver.value, v)

    # Print summary
    bread_map = v["bread_map"]
    print("\nSolution:")
    for b_id in v["bread_ids"]:
        bq = chosen["bread_quantities"][b_id]
        rq = chosen["remaining_quantities"][b_id]
        print(
            f"  {bread_map[b_id].name}: {bq} baked, {bq - rq} delivered, {rq} remaining"
        )
    print(f"Sessions used: {len(chosen['stove_sessions'])}")
    for i, sess in enumerate(chosen["stove_sessions"], 1):
        layers_str = []
        for lay_info in sess:
            if lay_info is None:
                layers_str.append("empty")
            else:
                b_id, qty = lay_info
                layers_str.append(f"{bread_map[b_id].name}×{qty}")
        print(f"  Session {i}: {', '.join(layers_str)}")

    return BakingPlanResult(
        bread_quantities=chosen["bread_quantities"],
        remaining_quantities=chosen["remaining_quantities"],
        stove_sessions=chosen["stove_sessions"],
        distribution=chosen["distribution"],
        total_deliveries=total_deliveries,
        sessions_used=len(chosen["stove_sessions"]),
    )


def solve_bread_planning_all(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],
    max_sessions: int = 10,
    time_limit_seconds: int = 60,
    max_solutions: int = 5,
) -> list[dict] | None:
    """
    Run the solver and return ALL collected solutions as a list of dicts.
    Returns None if no solutions found.
    """
    if not available_breads or not pickup_locations:
        return None

    for b in available_breads:
        if not b.pieces_per_stove_layer:
            print(f"⚠️  Bread {b.name} has EMPTY pieces_per_stove_layer!")
            return None

    # No symmetry breaking for diverse solutions
    model, v = _build_model(
        available_breads,
        pickup_locations,
        capacities,
        max_sessions,
        symmetry_breaking=False,
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_workers = 8
    solver.parameters.log_search_progress = True
    solver.parameters.enumerate_all_solutions = False

    def make_extractor(vd):
        def extract(callback):
            sol = _extract_solution(callback.value, vd)
            sol["objective"] = callback.objective_value
            return sol

        return extract

    collector = BreadSolutionCollector(max_solutions, make_extractor(v))
    status = solver.solve(model, collector)

    print(f"\nSolver status: {solver.status_name(status)}")
    print(f"Raw solutions found: {len(collector.solutions)}")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    if not collector.solutions:
        return None

    return collector.get_best_solutions()


# ---------------------------------------------------------------------------
# Django integration helpers
# ---------------------------------------------------------------------------


def collect_solver_input(
    year: int,
    delivery_week: int,
    delivery_day: int | None = None,
) -> dict | None:
    """
    Pull data from Django models and return solver input as a dict.
    Returns None if there's no data to solve.
    """
    from collections import defaultdict

    from tapir.bakery.models import (
        AvailableBreadsForDeliveryDay,
        Bread,
        BreadCapacityPickupLocation,
        BreadDelivery,
    )

    print("\n" + "=" * 80)
    print(
        f"COLLECT_SOLVER_INPUT: year={year}, week={delivery_week}, day={delivery_day}"
    )
    print("=" * 80)

    available_qs = AvailableBreadsForDeliveryDay.objects.filter(
        year=year, delivery_week=delivery_week
    )
    if delivery_day is not None:
        available_qs = available_qs.filter(delivery_day=delivery_day)

    available_bread_ids = available_qs.values_list("bread_id", flat=True).distinct()
    breads_qs = Bread.objects.filter(id__in=available_bread_ids, is_active=True)
    available_breads = [
        BreadInfo(
            bread_id=b.id,
            name=b.name,
            pieces_per_stove_layer=b.pieces_per_stove_layer or [],
            can_span_sessions=b.one_batch_can_be_baked_in_more_than_one_stove,
            min_pieces=b.min_pieces,
            max_pieces=b.max_pieces,
            min_remaining_pieces=b.min_remaining_pieces or 0,
        )
        for b in breads_qs
    ]

    if not available_breads:
        print("No available breads found!")
        return None

    deliveries_qs = BreadDelivery.objects.filter(
        year=year, delivery_week=delivery_week
    ).select_related("pickup_location", "bread")
    deliveries = list(deliveries_qs)

    if delivery_day is not None:
        deliveries = [
            d for d in deliveries if d.pickup_location.delivery_day == delivery_day
        ]

    if not deliveries:
        print("No deliveries found!")
        return None

    location_data = defaultdict(lambda: {"total": 0, "fixed_demand": defaultdict(int)})
    for d in deliveries:
        loc_id = d.pickup_location_id
        location_data[loc_id]["total"] += 1
        if d.bread_id:
            location_data[loc_id]["fixed_demand"][d.bread_id] += 1

    pickup_locations = []
    for d in deliveries:
        loc_id = d.pickup_location_id
        if not any(pl.location_id == loc_id for pl in pickup_locations):
            pickup_locations.append(
                PickupLocationInfo(
                    location_id=loc_id,
                    name=d.pickup_location.name,
                    total_deliveries=location_data[loc_id]["total"],
                    fixed_demand=dict(location_data[loc_id]["fixed_demand"]),
                )
            )

    if not pickup_locations:
        print("No pickup locations found!")
        return None

    caps_qs = BreadCapacityPickupLocation.objects.filter(
        year=year, delivery_week=delivery_week
    ).select_related("pickup_location")

    if delivery_day is not None:
        caps_list = [
            c for c in caps_qs if c.pickup_location.delivery_day == delivery_day
        ]
    else:
        caps_list = list(caps_qs)

    capacities = {(c.bread_id, c.pickup_location_id): c.capacity for c in caps_list}

    for bread in available_breads:
        for loc in pickup_locations:
            if (bread.bread_id, loc.location_id) not in capacities:
                capacities[(bread.bread_id, loc.location_id)] = loc.total_deliveries
                print(
                    f"  ⚠️  Missing capacity for {bread.name} at {loc.name}, "
                    f"defaulting to {loc.total_deliveries}"
                )

    return {
        "available_breads": available_breads,
        "pickup_locations": pickup_locations,
        "capacities": capacities,
    }


def save_solution_to_db(
    year: int,
    delivery_week: int,
    delivery_day: int | None,
    solution: dict,
) -> None:
    """Save a solver solution dict to the database."""
    from django.db import transaction

    from tapir.bakery.models import (
        BreadDelivery,
        BreadsPerPickupLocationPerWeek,
        StoveSession,
    )

    with transaction.atomic():
        if delivery_day is not None:
            deliveries = BreadDelivery.objects.filter(
                year=year, delivery_week=delivery_week
            ).select_related("pickup_location")
            location_ids = list(
                set(
                    d.pickup_location_id
                    for d in deliveries
                    if d.pickup_location.delivery_day == delivery_day
                )
            )
        else:
            location_ids = None

        delete_dist_qs = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year, delivery_week=delivery_week
        )
        if location_ids is not None:
            delete_dist_qs = delete_dist_qs.filter(pickup_location_id__in=location_ids)
        delete_dist_qs.delete()

        delete_sess_qs = StoveSession.objects.filter(
            year=year, delivery_week=delivery_week
        )
        if delivery_day is not None:
            delete_sess_qs = delete_sess_qs.filter(delivery_day=delivery_day)
        delete_sess_qs.delete()

        # Create distribution records
        dist_objects = []
        for key, count in solution["distribution"].items():
            if count > 0:
                if isinstance(key, tuple):
                    bread_id, pickup_location_id = key
                else:
                    bread_id, pickup_location_id = str(key).split(",")
                dist_objects.append(
                    BreadsPerPickupLocationPerWeek(
                        year=year,
                        delivery_week=delivery_week,
                        bread_id=bread_id,
                        pickup_location_id=pickup_location_id,
                        count=count,
                    )
                )
        if dist_objects:
            BreadsPerPickupLocationPerWeek.objects.bulk_create(dist_objects)

        # Create stove session records — only for used layers
        session_objects = []
        for sess_num, session in enumerate(solution["stove_sessions"], start=1):
            for layer_num, layer_info in enumerate(session, start=1):
                if layer_info is None:
                    continue
                bread_id, quantity = layer_info
                session_objects.append(
                    StoveSession(
                        year=year,
                        delivery_week=delivery_week,
                        delivery_day=delivery_day,
                        session_number=sess_num,
                        layer_number=layer_num,
                        bread_id=bread_id,
                        quantity=quantity,
                    )
                )
        if session_objects:
            StoveSession.objects.bulk_create(session_objects)


def solve_and_save(
    year: int,
    delivery_week: int,
    delivery_day: int | None = None,
    max_solutions: int = 1,
    solution_index: int = 0,
) -> BakingPlanResult | None:
    """Pull data, run solver, save results back to DB."""
    solver_input = collect_solver_input(year, delivery_week, delivery_day)
    if solver_input is None:
        return None

    result = solve_bread_planning(
        available_breads=solver_input["available_breads"],
        pickup_locations=solver_input["pickup_locations"],
        capacities=solver_input["capacities"],
        max_solutions=max_solutions,
        solution_index=solution_index,
    )

    if result is None:
        return None

    solution_dict = {
        "bread_quantities": result.bread_quantities,
        "remaining_quantities": result.remaining_quantities,
        "stove_sessions": result.stove_sessions,
        "distribution": result.distribution,
    }
    save_solution_to_db(year, delivery_week, delivery_day, solution_dict)

    return result
