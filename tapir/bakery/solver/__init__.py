"""
Weekly bread planning: how many of each bread to bake, in which stove sessions,
and how to distribute them across the pickup locations.
"""

from tapir.bakery.solver.dataclasses import (
    BakingPlanResult,
    BreadInfo,
    PickupLocationInfo,
    SolverDiagnostic,
    SolverResult,
)
from tapir.bakery.solver.django_integration import (
    collect_solver_input,
    save_solution_to_db,
    solve_and_save,
)
from tapir.bakery.solver.solve import (
    solve_bread_planning,
    solve_bread_planning_all,
)

__all__ = [
    "BakingPlanResult",
    "BreadInfo",
    "PickupLocationInfo",
    "collect_solver_input",
    "save_solution_to_db",
    "solve_and_save",
    "solve_bread_planning",
    "solve_bread_planning_all",
]
