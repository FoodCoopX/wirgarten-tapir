"""
Whether the CP-SAT solver is installed.

Outside tapir.bakery.solver, because importing anything from that package
executes its __init__, which imports the ortools-backed modules: a check living
in there would only be reachable once the thing it checks for is present.

ortools is an optional dependency (the "bakery" extra in pyproject.toml): it
and its subtree - numpy, pandas, protobuf, absl-py, immutabledict - are about
210 MB, and nothing outside this package imports them. An installation built
without the extra gets a clear answer from the two solver endpoints rather than
an ImportError traceback.
"""

from importlib.util import find_spec

SOLVER_UNAVAILABLE_MESSAGE = (
    "Der Solver ist auf dieser Installation nicht verfügbar: das Paket "
    "'ortools' fehlt. Installiere die Abhängigkeiten mit "
    "'poetry install --extras bakery'."
)


def is_solver_available() -> bool:
    # find_spec rather than a try/import: this is called on a request path and
    # importing ortools costs real time and memory. It returns None for a
    # missing top-level module, and raises for a broken or partially removed
    # distribution; "unavailable" is the right answer in both cases.
    try:
        return find_spec("ortools") is not None
    except (ImportError, ValueError):
        return False
