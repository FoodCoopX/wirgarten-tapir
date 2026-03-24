from tapir.bakery.solver.dataclasses import SolverResult
from tapir.bakery.solver.preferences import get_member_preferences
from tapir.bakery.solver.solve import solve_bread_planning


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
        BreadSpecificsPerDeliveryDay,
    )
    from tapir.bakery.solver.dataclasses import BreadInfo, PickupLocationInfo
    from tapir.wirgarten.parameter_keys import ParameterKeys
    from tapir.wirgarten.utils import get_parameter_value

    print("\n" + "=" * 80)
    print(
        f"COLLECT_SOLVER_INPUT: year={year}, week={delivery_week}, day={delivery_day}"
    )
    print("=" * 80)

    # Get stove layers from parameter
    stove_layers = get_parameter_value(ParameterKeys.BAKERY_STOVE_LAYERS)
    if stove_layers is None:
        stove_layers = 4
    stove_layers = int(stove_layers)

    # ── Available breads ─────────────────────────────────────────────

    available_qs = AvailableBreadsForDeliveryDay.objects.filter(
        year=year, delivery_week=delivery_week
    )
    if delivery_day is not None:
        available_qs = available_qs.filter(delivery_day=delivery_day)

    available_bread_ids = available_qs.values_list("bread_id", flat=True).distinct()
    breads_qs = Bread.objects.filter(id__in=available_bread_ids, is_active=True)

    # ── Day-specific overrides ───────────────────────────────────────

    specifics_qs = BreadSpecificsPerDeliveryDay.objects.filter(
        year=year, delivery_week=delivery_week
    )
    if delivery_day is not None:
        specifics_qs = specifics_qs.filter(delivery_day=delivery_day)

    specifics_by_bread = {s.bread_id: s for s in specifics_qs}

    # ── Build BreadInfo list with overrides ──────────────────────────

    available_breads = []
    for b in breads_qs:
        specifics = specifics_by_bread.get(b.id)
        fixed_pieces = None

        if specifics and specifics.fixed_pieces is not None:
            fixed_pieces = specifics.fixed_pieces
            # fixed_pieces overrides min/max entirely
            min_pieces = None
            max_pieces = None
        else:
            min_pieces = (
                specifics.min_pieces
                if specifics and specifics.min_pieces is not None
                else b.min_pieces
            )
            max_pieces = (
                specifics.max_pieces
                if specifics and specifics.max_pieces is not None
                else b.max_pieces
            )

        min_remaining = (
            specifics.min_remaining_pieces
            if specifics and specifics.min_remaining_pieces is not None
            else (b.min_remaining_pieces or 0)
        )

        available_breads.append(
            BreadInfo(
                bread_id=b.id,
                name=b.name,
                pieces_per_stove_layer=b.pieces_per_stove_layer or [],
                can_span_sessions=b.one_batch_can_be_baked_in_more_than_one_stove,
                min_pieces=min_pieces,
                max_pieces=max_pieces,
                min_remaining_pieces=min_remaining,
                fixed_pieces=fixed_pieces,
            )
        )

    if not available_breads:
        print("No available breads found!")
        return None

    # ── Deliveries ───────────────────────────────────────────────────

    deliveries_qs = BreadDelivery.objects.filter(
        year=year, delivery_week=delivery_week, joker_taken=False
    ).select_related("pickup_location", "bread")
    deliveries = list(deliveries_qs)

    if delivery_day is not None:
        deliveries = [
            d for d in deliveries if d.pickup_location.delivery_day == delivery_day
        ]

    if not deliveries:
        print("No deliveries found!")
        return None

    # ── Pickup locations ─────────────────────────────────────────────

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

    # ── Capacities ───────────────────────────────────────────────────

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

    member_preferences = get_member_preferences(year, delivery_week, delivery_day)

    if member_preferences:
        total_prefs = sum(len(mp["preferred_bread_ids"]) for mp in member_preferences)
        print(
            f"\nPreference data: {len(member_preferences)} members, {total_prefs} total entries"
        )
    else:
        print("\nNo preference data found — distribution will not be preference-aware.")

    return {
        "available_breads": available_breads,
        "pickup_locations": pickup_locations,
        "capacities": capacities,
        "stove_layers": stove_layers,
        "member_preferences": member_preferences,
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
        BreadsPerPickupLocationPerWeek,
        StoveSession,
    )

    with transaction.atomic():
        # Get location IDs from the solution's distribution
        if delivery_day is not None:
            location_ids = list(
                set(
                    key[1] if isinstance(key, tuple) else str(key).split(",")[1]
                    for key in solution.get("distribution", {}).keys()
                )
            )
        else:
            location_ids = None

        delete_dist_qs = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year, delivery_week=delivery_week
        )
        if location_ids:
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
) -> SolverResult:
    """
    Pull data, run solver, save results back to DB.

    Always returns a SolverResult. Check result.is_ok for success.
    """
    from tapir.bakery.solver.dataclasses import SolverDiagnostic

    solver_input = collect_solver_input(year, delivery_week, delivery_day)
    if solver_input is None:
        return SolverResult(
            plan=None,
            status="no_data",
            diagnostics=[
                SolverDiagnostic(
                    level="error",
                    category="no_data",
                    bread_name=None,
                    location_name=None,
                    message=(
                        f"No solver input data found for "
                        f"year={year}, week={delivery_week}, day={delivery_day}. "
                        f"Check that breads are available, deliveries exist, "
                        f"and pickup locations are configured."
                    ),
                )
            ],
        )

    result = solve_bread_planning(
        available_breads=solver_input["available_breads"],
        pickup_locations=solver_input["pickup_locations"],
        capacities=solver_input["capacities"],
        stove_layers=solver_input["stove_layers"],
        max_solutions=max_solutions,
        solution_index=solution_index,
        member_preferences=solver_input.get("member_preferences"),
    )

    if result.is_ok:
        solution_dict = {
            "bread_quantities": result.plan.bread_quantities,
            "remaining_quantities": result.plan.remaining_quantities,
            "stove_sessions": result.plan.stove_sessions,
            "distribution": result.plan.distribution,
            "diagnostics": [
                {
                    "level": d.level,
                    "category": d.category,
                    "bread_name": d.bread_name,
                    "location_name": d.location_name,
                    "message": d.message,
                }
                for d in result.diagnostics
            ],
        }
        save_solution_to_db(year, delivery_week, delivery_day, solution_dict)

    # Always print the summary
    print(result.summary())

    return result
