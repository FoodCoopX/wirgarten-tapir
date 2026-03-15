from ortools.sat.python import cp_model

from tapir.bakery.solver.collector import BreadSolutionCollector
from tapir.bakery.solver.dataclasses import (
    BakingPlanResult,
    BreadInfo,
    PickupLocationInfo,
    SolverDiagnostic,
    SolverResult,
)
from tapir.bakery.solver.diagnostics import diagnose_infeasibility
from tapir.bakery.solver.solver_model import build_model, extract_solution

# ---------------------------------------------------------------------------
# Core solver — single implementation for both preview and apply
# ---------------------------------------------------------------------------


def _run_solver(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],
    max_sessions: int = 10,
    stove_layers: int = 4,
    time_limit_seconds: int = 120,
    max_solutions: int = 10,
    member_preferences: list[dict] | None = None,
) -> tuple[list[dict], list[SolverDiagnostic], str]:
    """
    Core solver. Returns (solutions, diagnostics, status_str).

    solutions: list of solution dicts (may be empty)
    diagnostics: list of SolverDiagnostic
    status_str: one of 'optimal', 'feasible', 'infeasible', 'error', 'no_data', 'no_solutions'
    """
    diagnostics: list[SolverDiagnostic] = []

    # ── Validation ────────────────────────────────────────────────────

    if not available_breads:
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="no_data",
                bread_name=None,
                location_name=None,
                message="No available breads provided.",
            )
        )
        return [], diagnostics, "no_data"

    if not pickup_locations:
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="no_data",
                bread_name=None,
                location_name=None,
                message="No pickup locations provided.",
            )
        )
        return [], diagnostics, "no_data"

    for b in available_breads:
        if not b.pieces_per_stove_layer and b.fixed_pieces is None:
            diagnostics.append(
                SolverDiagnostic(
                    level="error",
                    category="no_data",
                    bread_name=b.name,
                    location_name=None,
                    message=(
                        f"Bread '{b.name}' has no pieces_per_stove_layer defined. "
                        f"Cannot determine how many pieces fit in a stove layer."
                    ),
                )
            )
            return [], diagnostics, "no_data"

    # ── Pre-solve diagnostics ─────────────────────────────────────────

    pre_diagnostics = diagnose_infeasibility(
        available_breads, pickup_locations, capacities, max_sessions, stove_layers
    )
    diagnostics.extend(pre_diagnostics)

    pre_errors = [d for d in pre_diagnostics if d.level == "error"]
    if pre_errors:
        print("\n" + "=" * 80)
        print("⚠️  PRE-SOLVE DIAGNOSTICS FOUND LIKELY ISSUES:")
        print("=" * 80)
        for d in pre_errors:
            print(f"  {d}")
        print()

    # ── Debug output ──────────────────────────────────────────────────

    total_deliveries = sum(loc.total_deliveries for loc in pickup_locations)

    print("=" * 80)
    print("SOLVER INPUT DEBUG")
    print("=" * 80)
    print(f"Available breads: {len(available_breads)}")
    for b in available_breads:
        print(f"  - {b.name} (id={b.bread_id})")
        print(f"    pieces_per_layer: {b.pieces_per_stove_layer}")
        print(f"    can_span_sessions: {b.can_span_sessions}")
        if b.fixed_pieces is not None:
            print(f"    fixed_pieces: {b.fixed_pieces}")
        else:
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
    print(f"Stove layers: {stove_layers}")

    if member_preferences:
        total_prefs = sum(len(mp["preferred_bread_ids"]) for mp in member_preferences)
        print(
            f"\nPreference data: {len(member_preferences)} members, {total_prefs} total entries"
        )
    else:
        print("\nNo preference data — distribution will not be preference-aware.")

    # ── Build model ───────────────────────────────────────────────────

    use_symmetry = max_solutions <= 1
    model, v = build_model(
        available_breads,
        pickup_locations,
        capacities,
        max_sessions,
        stove_layers,
        use_symmetry,
        member_preferences=member_preferences,
    )

    # ── Solve ─────────────────────────────────────────────────────────

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_workers = 8
    solver.parameters.log_search_progress = True
    solver.parameters.enumerate_all_solutions = False

    def make_extractor(vd):
        def extract(callback):
            sol = extract_solution(callback.value, vd)
            sol["objective"] = callback.objective_value
            return sol

        return extract

    collector = BreadSolutionCollector(max_solutions, make_extractor(v))
    solve_status = solver.solve(model, collector)

    print(f"\nSolver status: {solver.status_name(solve_status)}")
    print(f"Raw solutions found: {len(collector.solutions)}")

    # ── Handle solver status ──────────────────────────────────────────

    if solve_status == cp_model.INFEASIBLE:
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="infeasible",
                bread_name=None,
                location_name=None,
                message=(
                    "Solver confirmed: the problem is INFEASIBLE. "
                    "See diagnostics above for likely causes."
                ),
            )
        )
        _print_diagnostics_summary(diagnostics)
        return [], diagnostics, "infeasible"

    if solve_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="solver_error",
                bread_name=None,
                location_name=None,
                message=(
                    f"Solver returned unexpected status: "
                    f"{solver.status_name(solve_status)}. "
                    f"Try increasing the time limit."
                ),
            )
        )
        _print_diagnostics_summary(diagnostics)
        return [], diagnostics, "error"

    if not collector.solutions:
        _print_diagnostics_summary(diagnostics)
        return [], diagnostics, "no_solutions"

    # ── Extract & print solutions ─────────────────────────────────────

    solutions = collector.get_best_solutions()
    print(f"Good distinct solutions: {len(solutions)}")

    if not solutions:
        _print_diagnostics_summary(diagnostics)
        return [], diagnostics, "no_solutions"

    bread_map = v["bread_map"]
    for i, sol in enumerate(solutions):
        print(f"\n  Solution {i}: objective={sol.get('_objective', 'N/A')}")
        for b_id in v["bread_ids"]:
            bq = sol["bread_quantities"][b_id]
            rq = sol["remaining_quantities"][b_id]
            print(
                f"    {bread_map[b_id].name}: "
                f"{bq} baked, {bq - rq} delivered, {rq} remaining"
            )
        print(f"  Sessions used: {len(sol['stove_sessions'])}")
        for j, sess in enumerate(sol["stove_sessions"], 1):
            layers_str = []
            for lay_info in sess:
                if lay_info is None:
                    layers_str.append("empty")
                else:
                    b_id, qty = lay_info
                    layers_str.append(f"{bread_map[b_id].name}×{qty}")
            print(f"    Session {j}: {', '.join(layers_str)}")
        if sol.get("members_with_preferences", 0) > 0:
            met = sol["members_satisfied"]
            total = sol["members_with_preferences"]
            pct = (met / total * 100) if total else 0
            print(f"  Preference satisfaction: {met}/{total} members ({pct:.1f}%)")

    result_status = "optimal" if solve_status == cp_model.OPTIMAL else "feasible"

    _print_diagnostics_summary(diagnostics)
    return solutions, diagnostics, result_status


# ---------------------------------------------------------------------------
# Public API — thin wrappers
# ---------------------------------------------------------------------------


def solve_bread_planning(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],
    max_sessions: int = 10,
    stove_layers: int = 4,
    time_limit_seconds: int = 120,
    max_solutions: int = 1,
    solution_index: int = 0,
    member_preferences: list[dict] | None = None,
) -> SolverResult:
    """
    Solve and return a single SolverResult (used by solve_and_save / apply).
    """
    solutions, diagnostics, status_str = _run_solver(
        available_breads=available_breads,
        pickup_locations=pickup_locations,
        capacities=capacities,
        max_sessions=max_sessions,
        stove_layers=stove_layers,
        time_limit_seconds=time_limit_seconds,
        max_solutions=max_solutions,
        member_preferences=member_preferences,
    )

    if not solutions:
        return SolverResult(plan=None, status=status_str, diagnostics=diagnostics)

    idx = min(solution_index, len(solutions) - 1)
    chosen = solutions[idx]
    total_deliveries = sum(loc.total_deliveries for loc in pickup_locations)

    plan = BakingPlanResult(
        bread_quantities=chosen["bread_quantities"],
        remaining_quantities=chosen["remaining_quantities"],
        stove_sessions=chosen["stove_sessions"],
        distribution=chosen["distribution"],
        total_deliveries=total_deliveries,
        sessions_used=len(chosen["stove_sessions"]),
    )

    return SolverResult(plan=plan, status=status_str, diagnostics=diagnostics)


def solve_bread_planning_all(
    available_breads: list[BreadInfo],
    pickup_locations: list[PickupLocationInfo],
    capacities: dict[tuple[int, int], int],
    max_sessions: int = 10,
    stove_layers: int = 4,
    time_limit_seconds: int = 60,
    max_solutions: int = 10,
    member_preferences: list[dict] | None = None,
) -> dict:
    """
    Solve and return all solutions as raw dicts (used by the preview view).
    """
    solutions, diagnostics, status_str = _run_solver(
        available_breads=available_breads,
        pickup_locations=pickup_locations,
        capacities=capacities,
        max_sessions=max_sessions,
        stove_layers=stove_layers,
        time_limit_seconds=time_limit_seconds,
        max_solutions=max_solutions,
        member_preferences=member_preferences,
    )

    diagnostics_dicts = [
        {
            "level": d.level,
            "category": d.category,
            "bread_name": d.bread_name,
            "location_name": d.location_name,
            "message": d.message,
        }
        for d in diagnostics
    ]

    for sol in solutions:
        sol["diagnostics"] = diagnostics_dicts

    return {"solutions": solutions, "diagnostics": diagnostics_dicts}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_diagnostics_summary(diagnostics: list[SolverDiagnostic]):
    """Print diagnostics to stdout."""
    if not diagnostics:
        return
    errors = [d for d in diagnostics if d.level == "error"]
    warnings = [d for d in diagnostics if d.level == "warning"]
    infos = [d for d in diagnostics if d.level == "info"]

    print("\n" + "=" * 80)
    print("DIAGNOSTICS SUMMARY")
    print("=" * 80)
    if errors:
        print(f"\n{len(errors)} error(s):")
        for d in errors:
            print(f"  {d}")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for d in warnings:
            print(f"  {d}")
    if infos:
        print(f"\n{len(infos)} info(s):")
        for d in infos:
            print(f"  {d}")
    print()
