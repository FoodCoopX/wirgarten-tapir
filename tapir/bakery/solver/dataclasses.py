from dataclasses import dataclass, field


@dataclass
class BreadInfo:
    bread_id: int
    name: str
    pieces_per_stove_layer: list[int]  # e.g. [10, 11, 12]
    can_span_sessions: bool  # one_batch_can_be_baked_in_more_than_one_stove
    min_pieces: int | None  # minimum total pieces to bake (None = no minimum)
    max_pieces: int | None  # maximum total pieces to bake (None = no maximum)
    min_remaining_pieces: int  # minimum extra pieces beyond deliveries
    fixed_pieces: int | None = None  # if set, exactly this many must be baked


@dataclass
class PickupLocationInfo:
    location_id: int
    name: str
    total_deliveries: int  # Total number of delivery slots at this location
    # Fixed demand: bread_id -> count (from members who chose specific breads)
    fixed_demand: dict[int, int] = field(default_factory=dict)


@dataclass
class BakingPlanResult:
    """Output of the optimizer."""

    bread_quantities: dict[int, int]  # bread_id -> total quantity
    remaining_quantities: dict[int, int]  # bread_id -> remaining quantity
    stove_sessions: list[list[tuple[int, int] | None]]  # sessions x layers
    distribution: dict[tuple[int, int], int]  # (bread_id, location_id) -> count
    total_deliveries: int
    sessions_used: int


@dataclass
class SolverDiagnostic:
    """A single diagnostic message about why the solver might fail."""

    level: str  # "error", "warning", "info"
    category: str  # e.g. "capacity", "min_max", "fixed_pieces", "stove"
    bread_name: str | None
    location_name: str | None
    message: str

    def __str__(self):
        prefix = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(self.level, "?")
        return f"{prefix} [{self.category}] {self.message}"


@dataclass
class SolverResult:
    """Extended result that includes diagnostics."""

    plan: BakingPlanResult | None
    status: str  # "optimal", "feasible", "infeasible", "no_data", "error"
    diagnostics: list[SolverDiagnostic] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return self.plan is not None

    @property
    def errors(self) -> list[SolverDiagnostic]:
        return [d for d in self.diagnostics if d.level == "error"]

    @property
    def warnings(self) -> list[SolverDiagnostic]:
        return [d for d in self.diagnostics if d.level == "warning"]

    def summary(self) -> str:
        lines = []
        if self.plan:
            lines.append(f"✅ Solution found ({self.status})")
            lines.append(
                f"   Sessions: {self.plan.sessions_used}, "
                f"Deliveries: {self.plan.total_deliveries}"
            )
        else:
            lines.append(f"🚫 No solution ({self.status})")
        for d in self.diagnostics:
            lines.append(f"   {d}")
        return "\n".join(lines)
