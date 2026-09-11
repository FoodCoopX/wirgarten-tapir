"""
Bread Baking Optimizer
======================
Solves the weekly bread planning problem:
- How many of each bread to bake (respecting stove layer constraints)
- How to distribute breads across pickup locations (respecting capacities)
- Individual member deliveries with chosen breads are treated as fixed constraints

Uses OR-Tools CP-SAT solver for constraint programming.
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
