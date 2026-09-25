"""
Whether the CP-SAT solver is installed.

ortools is an optional dependency: the "bakery" extra in pyproject.toml.
"""

from importlib.util import find_spec

SOLVER_UNAVAILABLE_MESSAGE = (
    "Der Solver ist auf dieser Installation nicht verfügbar: das Paket "
    "'ortools' fehlt. Installiere die Abhängigkeiten mit "
    "'poetry install --extras bakery'."
)


def is_solver_available() -> bool:
    # find_spec raises for a broken or partially removed distribution.
    try:
        return find_spec("ortools") is not None
    except (ImportError, ValueError):
        return False
