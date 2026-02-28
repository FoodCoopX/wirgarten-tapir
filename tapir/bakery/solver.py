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

    # How many of each bread to bake
    bread_quantities: dict[int, int]  # bread_id -> total quantity
    # Extra pieces beyond deliveries (for external sale etc.)
    remaining_quantities: dict[int, int]  # bread_id -> remaining quantity
    # Stove plan: list of sessions, each session is a list of (bread_id, quantity) per layer
    stove_sessions: list[list[tuple[int, int]]]
    # Distribution: (bread_id, pickup_location_id) -> count
    distribution: dict[tuple[int, int], int]
    # Stats
    total_deliveries: int
    sessions_used: int


def solve_bread_planning(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],  # (bread_id, pickup_location_id) -> max
    max_sessions: int = 10,
    time_limit_seconds: int = 60,
) -> BakingPlanResult | None:
    """
    Solve the weekly bread planning problem.

    Args:
        available_breads: Breads available this week with stove properties.
        pickup_locations: Pickup locations with total deliveries and fixed demand.
        capacities: Max capacity per (bread_id, pickup_location_id).
        max_sessions: Upper bound on baking sessions.
        time_limit_seconds: Solver time limit.

    Returns:
        BakingPlanResult or None if infeasible.
    """
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

    if not available_breads:
        print("No available breads!")
        return None

    print(f"\nPickup locations: {len(pickup_locations)}")
    total_deliveries = sum(loc.total_deliveries for loc in pickup_locations)
    for loc in pickup_locations:
        print(
            f"  - {loc.name} (id={loc.location_id}): {loc.total_deliveries} deliveries"
        )
        if loc.fixed_demand:
            print(f"    Fixed demand: {loc.fixed_demand}")

    if not pickup_locations:
        print("No pickup locations!")
        return None

    # Check if any breads have no pieces_per_stove_layer
    for b in available_breads:
        if not b.pieces_per_stove_layer:
            print(f"⚠️  Bread {b.name} has EMPTY pieces_per_stove_layer!")
            return None

    model = cp_model.CpModel()

    bread_map = {b.bread_id: b for b in available_breads}
    bread_ids = list(bread_map.keys())
    location_ids = [loc.location_id for loc in pickup_locations]
    location_map = {loc.location_id: loc for loc in pickup_locations}

    # -----------------------------------------------------------------------
    # Decision variables
    # -----------------------------------------------------------------------

    # 1. Distribution per (bread, location) - TOTAL count including fixed
    distribution_vars = {}
    for b_id in bread_ids:
        for loc in pickup_locations:
            fixed = loc.fixed_demand.get(b_id, 0)
            max_at_location = capacities.get((b_id, loc.location_id), 0)

            # Variable represents TOTAL at this location (fixed + flexible)
            distribution_vars[b_id, loc.location_id] = model.new_int_var(
                fixed,  # At least the fixed demand
                max_at_location,  # At most the capacity
                f"dist_{b_id}_{loc.location_id}",
            )

    # 2. Stove layers
    layer = {}
    layer_used = {}
    session_used = {}

    for sess in range(max_sessions):
        session_used[sess] = model.new_bool_var(f"sess_used_{sess}")
        for lay in range(4):
            layer_used[sess, lay] = model.new_bool_var(f"layer_used_{sess}_{lay}")
            for b_id in bread_ids:
                bread = bread_map[b_id]
                for qi, qty in enumerate(bread.pieces_per_stove_layer):
                    layer[sess, lay, b_id, qi] = model.new_bool_var(
                        f"layer_{sess}_{lay}_{b_id}_{qi}"
                    )

    # 3. Total baked per bread type
    total_baked = {}
    for b_id in bread_ids:
        bread = bread_map[b_id]
        lb = bread.min_pieces if bread.min_pieces is not None else 0
        ub = bread.max_pieces if bread.max_pieces is not None else total_deliveries * 2
        total_baked[b_id] = model.new_int_var(lb, ub, f"total_{b_id}")

    # 4. Remaining pieces per bread
    remaining = {}
    for b_id in bread_ids:
        bread = bread_map[b_id]
        max_remaining = (
            bread.max_pieces if bread.max_pieces is not None else total_deliveries * 2
        )
        remaining[b_id] = model.new_int_var(0, max_remaining, f"remaining_{b_id}")

    # 5. Min and max bread count per pickup location (for variety)
    min_bread_at_location = {}
    max_bread_at_location = {}
    for loc in pickup_locations:
        min_bread_at_location[loc.location_id] = model.new_int_var(
            0, loc.total_deliveries, f"min_at_{loc.location_id}"
        )
        max_bread_at_location[loc.location_id] = model.new_int_var(
            0, loc.total_deliveries, f"max_at_{loc.location_id}"
        )

    # 6. Session span tracking per bread
    bread_in_session = {}
    sessions_used_per_bread = {}
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.can_span_sessions:
            sessions_used_per_bread[b_id] = model.new_int_var(
                0, max_sessions, f"sessions_for_{b_id}"
            )
            for sess in range(max_sessions):
                bread_in_session[b_id, sess] = model.new_bool_var(
                    f"bread_{b_id}_in_sess_{sess}"
                )

    # -----------------------------------------------------------------------
    # Constraints
    # -----------------------------------------------------------------------

    # C1: Each location must distribute exactly its total deliveries
    for loc in pickup_locations:
        model.add(
            sum(distribution_vars[b_id, loc.location_id] for b_id in bread_ids)
            == loc.total_deliveries
        )

    # C2: Each stove layer is assigned to at most one (bread, qty) combo
    for sess in range(max_sessions):
        for lay in range(4):
            all_options = []
            for b_id in bread_ids:
                bread = bread_map[b_id]
                for qi in range(len(bread.pieces_per_stove_layer)):
                    all_options.append(layer[sess, lay, b_id, qi])

            model.add(sum(all_options) <= 1)
            model.add(layer_used[sess, lay] == sum(all_options))

    # C3: Session used iff any of its layers are used
    for sess in range(max_sessions):
        for lay in range(4):
            model.add(layer_used[sess, lay] <= session_used[sess])
        model.add(session_used[sess] <= sum(layer_used[sess, lay] for lay in range(4)))

    # C4: Total baked per bread = sum over all layers
    for b_id in bread_ids:
        bread = bread_map[b_id]
        layer_contributions = []
        for sess in range(max_sessions):
            for lay in range(4):
                for qi, qty in enumerate(bread.pieces_per_stove_layer):
                    layer_contributions.append(qty * layer[sess, lay, b_id, qi])

        model.add(total_baked[b_id] == sum(layer_contributions))

    # C5: Total baked = delivery demand + remaining
    for b_id in bread_ids:
        bread = bread_map[b_id]
        total_distributed = sum(
            distribution_vars[b_id, loc.location_id] for loc in pickup_locations
        )
        model.add(total_baked[b_id] == total_distributed + remaining[b_id])
        model.add(remaining[b_id] >= bread.min_remaining_pieces)

    # C6: Breads that CAN'T span sessions
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if not bread.can_span_sessions:
            bread_in_single_session = {}
            for sess in range(max_sessions):
                bread_in_single_session[sess] = model.new_bool_var(
                    f"bread_in_sess_{b_id}_{sess}"
                )
                has_bread = []
                for lay in range(4):
                    for qi in range(len(bread.pieces_per_stove_layer)):
                        has_bread.append(layer[sess, lay, b_id, qi])

                model.add(sum(has_bread) >= 1).only_enforce_if(
                    bread_in_single_session[sess]
                )
                model.add(sum(has_bread) == 0).only_enforce_if(
                    bread_in_single_session[sess].Not()
                )

            model.add(
                sum(bread_in_single_session[sess] for sess in range(max_sessions)) <= 1
            )

    # C7: Symmetry breaking
    for sess in range(1, max_sessions):
        model.add(session_used[sess] <= session_used[sess - 1])

    # C8: Track min and max bread counts per location (for variety)
    for loc in pickup_locations:
        for b_id in bread_ids:
            model.add(
                min_bread_at_location[loc.location_id]
                <= distribution_vars[b_id, loc.location_id]
            )
            model.add(
                max_bread_at_location[loc.location_id]
                >= distribution_vars[b_id, loc.location_id]
            )

    # C9: Enforce minimum variety at each location
    for loc in pickup_locations:
        if loc.total_deliveries >= len(bread_ids):
            # Ensure at least some of each bread at locations with enough demand
            target_per_bread = loc.total_deliveries // len(bread_ids)
            min_per_bread = max(1, target_per_bread // 2)

            for b_id in bread_ids:
                cap = capacities.get((b_id, loc.location_id), 0)
                if cap >= min_per_bread:
                    model.add(distribution_vars[b_id, loc.location_id] >= min_per_bread)
                    print(
                        f"  Variety: {bread_map[b_id].name} at {loc.name} >= {min_per_bread}"
                    )

    # C10: Track session span for breads that CAN span sessions
    for b_id in bread_ids:
        bread = bread_map[b_id]
        if bread.can_span_sessions:
            for sess in range(max_sessions):
                has_bread = []
                for lay in range(4):
                    for qi in range(len(bread.pieces_per_stove_layer)):
                        has_bread.append(layer[sess, lay, b_id, qi])

                model.add(sum(has_bread) >= 1).only_enforce_if(
                    bread_in_session[b_id, sess]
                )
                model.add(sum(has_bread) == 0).only_enforce_if(
                    bread_in_session[b_id, sess].Not()
                )

            model.add(
                sessions_used_per_bread[b_id]
                == sum(bread_in_session[b_id, sess] for sess in range(max_sessions))
            )

    # -----------------------------------------------------------------------
    # Objective
    # -----------------------------------------------------------------------

    VARIETY_WEIGHT = 1000
    SESSION_SPAN_WEIGHT = 50
    REMAINING_WEIGHT = 10
    SESSION_WEIGHT = 1

    remaining_penalty = sum(remaining[b_id] for b_id in bread_ids)
    session_penalty = sum(session_used[sess] for sess in range(max_sessions))

    # Variety: minimize difference between max and min at each location
    variety_penalty = sum(
        max_bread_at_location[loc.location_id] - min_bread_at_location[loc.location_id]
        for loc in pickup_locations
    )

    # Session span: minimize sessions per bread
    session_span_penalty = sum(
        sessions_used_per_bread[b_id]
        for b_id in bread_ids
        if b_id in sessions_used_per_bread
    )

    model.maximize(
        -VARIETY_WEIGHT * variety_penalty
        - SESSION_SPAN_WEIGHT * session_span_penalty
        - REMAINING_WEIGHT * remaining_penalty
        - SESSION_WEIGHT * session_penalty
    )

    # -----------------------------------------------------------------------
    # Solve
    # -----------------------------------------------------------------------
    print("\nStarting solver...")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_workers = 8
    solver.parameters.log_search_progress = True

    status = solver.solve(model)

    print(f"\nSolver finished with status: {solver.status_name(status)}")
    print(f"Wall time: {solver.wall_time}s")
    print(f"Objective value: {solver.objective_value}")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"No solution found! Status: {solver.status_name(status)}")
        return None

    # -----------------------------------------------------------------------
    # Extract solution
    # -----------------------------------------------------------------------

    bread_quantities = {b_id: solver.value(total_baked[b_id]) for b_id in bread_ids}
    remaining_quantities = {b_id: solver.value(remaining[b_id]) for b_id in bread_ids}

    print("\nSolution:")
    for b_id in bread_ids:
        bread = bread_map[b_id]
        total = bread_quantities[b_id]
        rem = remaining_quantities[b_id]
        sessions_span = (
            solver.value(sessions_used_per_bread[b_id])
            if b_id in sessions_used_per_bread
            else 1
        )
        print(
            f"  {bread.name}: {total} total ({total - rem} deliveries + {rem} remaining) "
            f"across {sessions_span} session(s)"
        )

    # Stove sessions
    stove_sessions = []
    for sess in range(max_sessions):
        if not solver.value(session_used[sess]):
            continue
        session_layers = []
        for lay in range(4):
            if not solver.value(layer_used[sess, lay]):
                session_layers.append(None)
                continue
            for b_id in bread_ids:
                bread = bread_map[b_id]
                for qi, qty in enumerate(bread.pieces_per_stove_layer):
                    if solver.value(layer[sess, lay, b_id, qi]):
                        session_layers.append((b_id, qty))
                        break
                else:
                    continue
                break
        stove_sessions.append(session_layers)

    # Distribution
    distribution: dict[tuple[int, int], int] = {}
    for b_id in bread_ids:
        for loc in pickup_locations:
            count = solver.value(distribution_vars[b_id, loc.location_id])
            if count > 0:
                distribution[(b_id, loc.location_id)] = count

    print("\nDistribution per location:")
    for loc in pickup_locations:
        print(f"  {loc.name}:")
        for b_id in bread_ids:
            count = distribution.get((b_id, loc.location_id), 0)
            if count > 0:
                fixed = loc.fixed_demand.get(b_id, 0)
                flexible = count - fixed
                print(
                    f"    {bread_map[b_id].name}: {count} "
                    f"(fixed: {fixed}, flexible: {flexible})"
                )

    print(f"\nSessions used: {len(stove_sessions)}")

    return BakingPlanResult(
        bread_quantities=bread_quantities,
        remaining_quantities=remaining_quantities,
        stove_sessions=stove_sessions,
        distribution=distribution,
        total_deliveries=total_deliveries,
        sessions_used=len(stove_sessions),
    )


# ---------------------------------------------------------------------------
# Django integration
# ---------------------------------------------------------------------------


def solve_and_save(
    year: int, delivery_week: int, delivery_day: int | None = None
) -> BakingPlanResult | None:
    """
    Pull data from Django models, run the solver, save results back to DB.
    """
    from collections import defaultdict

    from django.db import transaction

    from tapir.bakery.models import (
        AvailableBreadsForDeliveryDay,
        Bread,
        BreadCapacityPickupLocation,
        BreadDelivery,
        BreadsPerPickupLocationPerWeek,
        StoveSession,
    )

    print("\n" + "=" * 80)
    print(f"SOLVE_AND_SAVE: year={year}, week={delivery_week}, day={delivery_day}")
    print("=" * 80)

    # 1. Get available breads
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
        print("ERROR: No available breads found!")
        return None

    # 2. Get all deliveries
    deliveries_qs = BreadDelivery.objects.filter(
        year=year, delivery_week=delivery_week
    ).select_related("pickup_location", "bread")

    deliveries = list(deliveries_qs)

    # Filter by delivery_day if specified
    if delivery_day is not None:
        deliveries = [
            d for d in deliveries if d.pickup_location.delivery_day == delivery_day
        ]

    # 3. Build pickup location info with fixed demand
    location_data = defaultdict(lambda: {"total": 0, "fixed_demand": defaultdict(int)})

    for d in deliveries:
        loc_id = d.pickup_location_id
        location_data[loc_id]["total"] += 1
        if d.bread_id:  # If member chose a specific bread
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
        print("ERROR: No pickup locations found!")
        return None

    # 4. Get capacities
    caps_qs = BreadCapacityPickupLocation.objects.filter(
        year=year, delivery_week=delivery_week
    ).select_related("pickup_location")

    if delivery_day is not None:
        caps_qs = [c for c in caps_qs if c.pickup_location.delivery_day == delivery_day]
    else:
        caps_qs = list(caps_qs)

    capacities = {(c.bread_id, c.pickup_location_id): c.capacity for c in caps_qs}

    # Fill missing capacities with 0
    for bread in available_breads:
        for loc in pickup_locations:
            if (bread.bread_id, loc.location_id) not in capacities:
                capacities[(bread.bread_id, loc.location_id)] = 0

    # 5. Solve
    result = solve_bread_planning(
        available_breads=available_breads,
        pickup_locations=pickup_locations,
        capacities=capacities,
    )

    if result is None:
        print("ERROR: Solver returned no solution!")
        return None

    # 6. Save to BreadsPerPickupLocationPerWeek
    with transaction.atomic():
        # Delete old records
        delete_qs = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year, delivery_week=delivery_week
        )
        if delivery_day is not None:
            location_ids = [loc.location_id for loc in pickup_locations]
            delete_qs = delete_qs.filter(pickup_location_id__in=location_ids)
        delete_qs.delete()

        StoveSession.objects.filter(
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
        ).delete()

        # Create new records for distribution
        bulk_objects = []
        for (bread_id, pickup_location_id), count in result.distribution.items():
            if count > 0:
                bulk_objects.append(
                    BreadsPerPickupLocationPerWeek(
                        year=year,
                        delivery_week=delivery_week,
                        bread_id=bread_id,
                        pickup_location_id=pickup_location_id,
                        count=count,
                    )
                )

        if bulk_objects:
            BreadsPerPickupLocationPerWeek.objects.bulk_create(bulk_objects)

        # Create new stove session records
        session_objects = []
        for sess_num, session in enumerate(result.stove_sessions, start=1):
            for layer_num, layer_info in enumerate(session, start=1):
                if layer_info is None:
                    # Empty layer - save with null bread
                    session_objects.append(
                        StoveSession(
                            year=year,
                            delivery_week=delivery_week,
                            delivery_day=delivery_day,
                            session_number=sess_num,
                            layer_number=layer_num,
                            bread_id=None,
                            quantity=0,
                        )
                    )
                else:
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

    print("\nSUCCESS: Solution saved to database (distribution + stove sessions)")
    return result
