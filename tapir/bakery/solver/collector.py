from ortools.sat.python import cp_model


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
    # Stove sessions
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
    stove_fp = "||".join(sorted(parts))

    # Distribution
    dist = sol.get("distribution", {})
    dist_parts = sorted(f"{k}={v}" for k, v in dist.items() if v > 0)
    dist_fp = ",".join(dist_parts)

    return f"{stove_fp}###{dist_fp}"
