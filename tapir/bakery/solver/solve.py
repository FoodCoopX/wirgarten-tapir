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

    total_deliveries = sum(loc.total_deliveries for loc in pickup_locations)

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
        return [], diagnostics, "error"

    if not collector.solutions:
        return [], diagnostics, "no_solutions"

    # ── Extract & print solutions ─────────────────────────────────────

    solutions = collector.get_best_solutions()

    if not solutions:
        return [], diagnostics, "no_solutions"

    result_status = "optimal" if solve_status == cp_model.OPTIMAL else "feasible"

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
