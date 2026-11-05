from django.conf import settings
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

# The solver preview view waits for the result inside the request.
PREVIEW_TIME_LIMIT_SECONDS = 60
# The second solve only evens out the spread, see _spread_evenly; it stops
# after this, or earlier when the first one has used up the time limit.
SPREAD_TIME_LIMIT_SECONDS = 5


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
    status_str is one of 'optimal', 'feasible', 'infeasible', 'error',
    'no_data', 'no_solutions'. 'optimal' refers to the plan itself; the even
    spread of _spread_evenly afterwards is best effort within its time limit.
    """
    diagnostics: list[SolverDiagnostic] = []

    if not available_breads:
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="no_data",
                bread_name=None,
                location_name=None,
                message="Keine backbaren Brote für diese Woche gefunden.",
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
                message="Keine Abholstationen für diesen Liefertag gefunden.",
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
                        f"Brot '{b.name}': keine Angabe, wie viele Stück auf eine "
                        f"Ofenlage passen."
                    ),
                )
            )
            return [], diagnostics, "no_data"

    pre_diagnostics = diagnose_infeasibility(
        available_breads, pickup_locations, capacities, max_sessions, stove_layers
    )
    diagnostics.extend(pre_diagnostics)

    # An over-subscribed capacity makes distribution_vars an int var with
    # lb > ub, and CP-SAT answers MODEL_INVALID rather than INFEASIBLE. Only
    # this category is fatal: the other error-level checks are estimates.
    if any(
        diagnostic.category == "fixed_demand_exceeds_capacity"
        for diagnostic in pre_diagnostics
    ):
        return [], diagnostics, "infeasible"

    model, v = build_model(
        available_breads,
        pickup_locations,
        capacities,
        max_sessions,
        stove_layers,
        symmetry_breaking=True,
        member_preferences=member_preferences,
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_workers = 8
    # The CP-SAT search log is hundreds of lines on stdout per request.
    solver.parameters.log_search_progress = settings.DEBUG
    solver.parameters.enumerate_all_solutions = False

    def make_extractor(vd):
        def extract(callback):
            sol = extract_solution(callback.value, vd)
            # The plan's own objective; the second solve optimises the spread.
            sol["objective"] = callback.value(vd["main_objective"])
            sol["spread"] = callback.value(vd["spread"])
            return sol

        return extract

    collector = BreadSolutionCollector(max_solutions, make_extractor(v))
    solve_status = solver.solve(model, collector)

    if solve_status == cp_model.INFEASIBLE:
        diagnostics.append(
            SolverDiagnostic(
                level="error",
                category="infeasible",
                bread_name=None,
                location_name=None,
                message=(
                    "Der Solver bestätigt: Die Aufgabe ist nicht lösbar. "
                    "Die möglichen Ursachen stehen in den Meldungen darüber."
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
                    f"Der Solver hat unerwartet mit Status "
                    f"{solver.status_name(solve_status)} abgebrochen."
                    + (
                        " Bei UNKNOWN hilft meist ein höheres Zeitlimit."
                        if solve_status == cp_model.UNKNOWN
                        else ""
                    )
                ),
            )
        )
        return [], diagnostics, "error"

    if not collector.solutions:
        return [], diagnostics, "no_solutions"

    spread_time = min(SPREAD_TIME_LIMIT_SECONDS, time_limit_seconds - solver.wall_time)
    solutions = []
    if spread_time >= 1:
        solutions = _spread_evenly(
            model, v, solver, make_extractor(v), max_solutions, spread_time
        )
    if not solutions:
        solutions = collector.get_best_solutions()

    if not solutions:
        return [], diagnostics, "no_solutions"

    result_status = "optimal" if solve_status == cp_model.OPTIMAL else "feasible"

    return solutions, diagnostics, result_status


def _spread_evenly(
    model: cp_model.CpModel,
    v: dict,
    solver: cp_model.CpSolver,
    extract,
    max_solutions: int,
    time_limit_seconds: float,
) -> list[dict]:
    """
    The second solve: keeps the first one's best objective, starts from its
    plan and looks only for a more even spread of the loaves over the
    stations. Together the two cannot be proven optimal in the time the
    preview has, while the first alone is quick. Returns nothing when no plan
    is found in time.

    It keeps the first objective's weighted sum, not each of its terms: an
    equally good plan can trade one term against another. It changes the
    model in place (hints, a constraint, the objective).
    """
    for index in range(len(model.proto.variables)):
        var = model.get_int_var_from_proto_index(index)
        model.add_hint(var, solver.value(var))
    model.add(v["main_objective"] >= round(solver.objective_value))
    model.maximize(-v["spread"])

    spread_solver = cp_model.CpSolver()
    spread_solver.parameters.max_time_in_seconds = time_limit_seconds
    spread_solver.parameters.num_workers = 8
    spread_solver.parameters.log_search_progress = settings.DEBUG

    collector = BreadSolutionCollector(max_solutions, extract)
    spread_solver.solve(model, collector)
    return collector.get_best_solutions()


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
    time_limit_seconds: int = PREVIEW_TIME_LIMIT_SECONDS,
    max_solutions: int = 10,
    member_preferences: list[dict] | None = None,
) -> dict:
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
