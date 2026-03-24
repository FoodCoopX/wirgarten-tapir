"""
Tests for the Bread Baking Optimizer (solver).

Tests are organized by layer:
1. Unit tests for pure solver logic (no Django DB)
2. Integration tests for Django helpers (collect_solver_input, save_solution_to_db)
"""

from unittest.mock import patch

from tapir.bakery.models import BreadDelivery
from tapir.bakery.solver.collector import _solution_fingerprint
from tapir.bakery.solver.dataclasses import (
    BreadInfo,
    PickupLocationInfo,
    SolverResult,
)
from tapir.bakery.solver.solve import solve_bread_planning, solve_bread_planning_all
from tapir.bakery.solver.solver_model import build_model
from tapir.bakery.tests.factories import (
    AvailableBreadsForDeliveryDayFactory,
    BreadCapacityPickupLocationFactory,
    BreadDeliveryFactory,
    BreadFactory,
    BreadSpecificsPerDeliveryDayFactory,
)
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

# ---------------------------------------------------------------------------
# Helpers to build test data (pure solver — no DB)
# ---------------------------------------------------------------------------

_SENTINEL = object()


def make_bread(
    bread_id=1,
    name="Roggenbrot",
    pieces_per_layer=_SENTINEL,
    can_span=False,
    min_pieces=None,
    max_pieces=None,
    min_remaining=0,
    fixed_pieces=None,
):
    if pieces_per_layer is _SENTINEL:
        pieces_per_layer = [10]
    return BreadInfo(
        bread_id=bread_id,
        name=name,
        pieces_per_stove_layer=pieces_per_layer,
        can_span_sessions=can_span,
        min_pieces=min_pieces,
        max_pieces=max_pieces,
        min_remaining_pieces=min_remaining,
        fixed_pieces=fixed_pieces,
    )


def make_location(location_id=1, name="Markt", total_deliveries=5, fixed_demand=None):
    return PickupLocationInfo(
        location_id=location_id,
        name=name,
        total_deliveries=total_deliveries,
        fixed_demand=fixed_demand or {},
    )


def make_capacities(breads, locations, default_cap=None):
    """Build capacities dict. default_cap=None means use location's total_deliveries."""
    caps = {}
    for b in breads:
        for loc in locations:
            cap = default_cap if default_cap is not None else loc.total_deliveries
            caps[(b.bread_id, loc.location_id)] = cap
    return caps


def assert_solver_success(result):
    """Assert that the solver returned a successful result with a plan."""
    assert result is not None
    assert isinstance(result, SolverResult)
    assert result.status == "optimal", (
        f"Expected status 'ok', got '{result.status}': {result.diagnostics}"
    )
    assert result.plan is not None


def assert_solver_failed(result):
    """Assert that the solver returned None or a non-ok result (infeasible/error/no_data)."""
    assert result is not None
    assert isinstance(result, SolverResult)
    assert result.status != "optimal", "Expected failure but got status 'ok'"
    assert result.plan is None


def create_pickup_location_with_delivery_day(day, **kwargs):
    """Create a PickupLocation with an opening time on the given day_of_week."""
    pl = PickupLocationFactory.create(**kwargs)
    PickupLocationOpeningTime.objects.create(
        pickup_location=pl,
        day_of_week=day,
        open_time="08:00",
        close_time="18:00",
    )
    return pl


def setup_bread_at_location(year, week, loc, bread, capacity=10):
    """Create BreadCapacityPickupLocation so that BreadDelivery validation passes."""
    BreadCapacityPickupLocationFactory(
        year=year,
        delivery_week=week,
        pickup_location=loc,
        bread=bread,
        capacity=capacity,
    )


def create_bread_delivery_without_validation(year, week, pickup_location, bread=None):
    """Create a BreadDelivery using the factory but bypassing model validation.

    BreadDelivery.clean() validates availability through multiple related models.
    In solver tests we control the full data setup, so we skip that validation.
    """

    with patch.object(BreadDelivery, "clean", return_value=None):
        return BreadDeliveryFactory(
            year=year,
            delivery_week=week,
            pickup_location=pickup_location,
            bread=bread,
        )


# ===========================================================================
# 1. Pure solver unit tests — no DB needed
# ===========================================================================


class TestSolverBasic:
    """Basic solver sanity checks."""

    def test_single_bread_single_location(self):
        """Simplest case: one bread type, one location."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=8)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        plan = result.plan
        assert plan.bread_quantities[1] >= 8
        assert plan.total_deliveries == 8
        assert plan.sessions_used >= 1

    def test_respects_min_pieces(self):
        """Solver must bake at least min_pieces."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], min_pieces=20)]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.bread_quantities[1] >= 20

    def test_respects_max_pieces(self):
        """Solver must not bake more than max_pieces."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], max_pieces=10)]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.bread_quantities[1] <= 10

    def test_respects_min_remaining(self):
        """Solver must leave at least min_remaining pieces undistributed."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], min_remaining=3)]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        remaining = result.plan.remaining_quantities[1]
        assert remaining >= 3

    def test_fixed_demand_honored(self):
        """Fixed demand at a location must appear in distribution."""
        breads = [
            make_bread(bread_id=1, name="Roggen", pieces_per_layer=[10]),
            make_bread(bread_id=2, name="Dinkel", pieces_per_layer=[10]),
        ]
        locations = [
            make_location(
                location_id=1,
                total_deliveries=8,
                fixed_demand={1: 3},
            ),
        ]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        roggen_at_loc1 = result.plan.distribution.get((1, 1), 0)
        assert roggen_at_loc1 >= 3

    def test_empty_breads_returns_no_data(self):
        """No available breads → no_data status."""
        locations = [make_location()]
        result = solve_bread_planning([], locations, {})
        assert_solver_failed(result)
        assert result.status == "no_data"

    def test_empty_locations_returns_no_data(self):
        """No pickup locations → no_data status."""
        breads = [make_bread()]
        result = solve_bread_planning(breads, [], {})
        assert_solver_failed(result)
        assert result.status == "no_data"

    def test_empty_pieces_per_layer_returns_no_data(self):
        """Bread with empty pieces_per_stove_layer → no_data status."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[])]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        assert breads[0].pieces_per_stove_layer == []

        result = solve_bread_planning(breads, locations, caps)
        assert_solver_failed(result)
        assert result.status == "no_data"


class TestSolverMultipleBreads:
    """Tests with multiple bread types."""

    def test_two_breads_one_location(self):
        """Two bread types distributed to one location."""
        breads = [
            make_bread(bread_id=1, name="Roggen", pieces_per_layer=[10]),
            make_bread(bread_id=2, name="Dinkel", pieces_per_layer=[8]),
        ]
        locations = [make_location(location_id=1, total_deliveries=10)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        total_dist = sum(v for (b, l), v in result.plan.distribution.items() if l == 1)
        assert total_dist == 10

    def test_two_breads_two_locations(self):
        """Two breads, two locations — distribution must match per location."""
        breads = [
            make_bread(bread_id=1, name="Roggen", pieces_per_layer=[10]),
            make_bread(bread_id=2, name="Dinkel", pieces_per_layer=[8]),
        ]
        locations = [
            make_location(location_id=1, name="Markt", total_deliveries=6),
            make_location(location_id=2, name="Hof", total_deliveries=4),
        ]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        dist_loc1 = sum(v for (b, l), v in result.plan.distribution.items() if l == 1)
        dist_loc2 = sum(v for (b, l), v in result.plan.distribution.items() if l == 2)
        assert dist_loc1 == 6
        assert dist_loc2 == 4

    def test_fixed_demand_forces_bread_to_be_baked(self):
        """If any location has fixed demand for a bread, it must be baked."""
        breads = [
            make_bread(bread_id=1, name="Roggen", pieces_per_layer=[10]),
            make_bread(bread_id=2, name="Dinkel", pieces_per_layer=[8]),
        ]
        locations = [
            make_location(
                location_id=1,
                total_deliveries=5,
                fixed_demand={2: 2},
            ),
        ]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.bread_quantities[2] >= 2


class TestStoveSessions:
    """Tests for stove session constraints."""

    def test_no_span_single_session(self):
        """Bread that can't span sessions appears in at most 1 session."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], can_span=False)]
        locations = [make_location(location_id=1, total_deliveries=8)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        sessions_with_bread = 0
        for sess in result.plan.stove_sessions:
            if any(info is not None and info[0] == 1 for info in sess):
                sessions_with_bread += 1
        assert sessions_with_bread <= 1

    def test_can_span_at_most_two_sessions(self):
        """Bread that CAN span is still limited to 2 sessions."""
        breads = [
            make_bread(
                bread_id=1,
                pieces_per_layer=[5],
                can_span=True,
                min_pieces=30,
            )
        ]
        locations = [make_location(location_id=1, total_deliveries=20)]
        caps = make_capacities(breads, locations, default_cap=30)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=10, stove_layers=4
        )

        assert_solver_success(result)
        sessions_with_bread = 0
        for sess in result.plan.stove_sessions:
            if any(info is not None and info[0] == 1 for info in sess):
                sessions_with_bread += 1
        assert sessions_with_bread <= 2

    def test_layer_packing_no_gaps(self):
        """Used layers should have no gaps — if layer N is used, layer N-1 must be too."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=15)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        for sess in result.plan.stove_sessions:
            last_used = -1
            for i, info in enumerate(sess):
                if info is not None:
                    last_used = i
            for i in range(last_used):
                assert sess[i] is not None, (
                    f"Gap in layers: layer {i} is None but layer {last_used} is used"
                )

    def test_minimizes_sessions(self):
        """Solver should prefer fewer sessions (highest priority)."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=8)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=10, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.sessions_used == 1

    def test_stove_layers_parameter(self):
        """Different stove_layers values change the result."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], can_span=True)]
        locations = [make_location(location_id=1, total_deliveries=25)]
        caps = make_capacities(breads, locations, default_cap=30)

        result_2 = solve_bread_planning(
            breads, locations, caps, max_sessions=10, stove_layers=2
        )
        result_4 = solve_bread_planning(
            breads, locations, caps, max_sessions=10, stove_layers=4
        )

        assert_solver_success(result_2)
        assert_solver_success(result_4)
        assert result_2.plan.sessions_used > result_4.plan.sessions_used
        assert result_4.plan.sessions_used == 1
        assert result_2.plan.sessions_used >= 2


class TestMultipleQuantityOptions:
    """Tests for breads with multiple pieces_per_stove_layer options."""

    def test_different_qty_options(self):
        """Bread with [8, 10, 12] should pick the best fit."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[8, 10, 12])]
        locations = [make_location(location_id=1, total_deliveries=10)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        for sess in result.plan.stove_sessions:
            for info in sess:
                if info is not None:
                    b_id, qty = info
                    assert qty in [8, 10, 12]


class TestCapacities:
    """Tests for capacity constraints."""

    def test_capacity_limits_distribution(self):
        """Distribution at a location can't exceed capacity."""
        breads = [
            make_bread(bread_id=1, name="Roggen", pieces_per_layer=[10]),
            make_bread(bread_id=2, name="Dinkel", pieces_per_layer=[10]),
        ]
        locations = [make_location(location_id=1, total_deliveries=10)]
        caps = {
            (1, 1): 3,
            (2, 1): 10,
        }

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        roggen_at_loc = result.plan.distribution.get((1, 1), 0)
        assert roggen_at_loc <= 3


class TestDistribution:
    """Tests for distribution correctness."""

    def test_total_distributed_equals_deliveries(self):
        """Sum of distribution per location must equal that location's deliveries."""
        breads = [
            make_bread(bread_id=1, name="Roggen", pieces_per_layer=[10]),
            make_bread(bread_id=2, name="Dinkel", pieces_per_layer=[8]),
        ]
        locations = [
            make_location(location_id=1, name="Markt", total_deliveries=7),
            make_location(location_id=2, name="Hof", total_deliveries=5),
        ]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        for loc in locations:
            loc_total = sum(
                v
                for (b_id, l_id), v in result.plan.distribution.items()
                if l_id == loc.location_id
            )
            assert loc_total == loc.total_deliveries

    def test_baked_equals_distributed_plus_remaining(self):
        """For each bread: baked = distributed + remaining."""
        breads = [
            make_bread(bread_id=1, name="Roggen", pieces_per_layer=[10]),
            make_bread(bread_id=2, name="Dinkel", pieces_per_layer=[8]),
        ]
        locations = [
            make_location(location_id=1, total_deliveries=7),
            make_location(location_id=2, total_deliveries=5),
        ]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        for b in breads:
            baked = result.plan.bread_quantities[b.bread_id]
            distributed = sum(
                v
                for (b_id, l_id), v in result.plan.distribution.items()
                if b_id == b.bread_id
            )
            remaining = result.plan.remaining_quantities[b.bread_id]
            assert baked == distributed + remaining


class TestSolverInfeasible:
    """Tests for infeasible scenarios."""

    def test_impossible_min_max_returns_error(self):
        """min_pieces > max_pieces → error/infeasible status."""
        breads = [
            make_bread(bread_id=1, pieces_per_layer=[10], min_pieces=50, max_pieces=5)
        ]
        locations = [make_location(location_id=1, total_deliveries=3)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_failed(result)
        assert result.status in ("error", "infeasible")

    def test_demand_exceeds_capacity_everywhere(self):
        """If capacity is 0 everywhere but deliveries > 0 → infeasible."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = {(1, 1): 0}

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_failed(result)
        assert result.status == "infeasible"


class TestFixedPieces:
    """Tests for fixed_pieces (pre-baked) breads."""

    def test_fixed_pieces_exact_quantity(self):
        """fixed_pieces bread is distributed exactly that amount (no stove needed)."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], fixed_pieces=10)]
        locations = [make_location(location_id=1, total_deliveries=10)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.bread_quantities[1] == 10

    def test_fixed_pieces_no_remaining(self):
        """fixed_pieces breads must have 0 remaining — all distributed."""
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], fixed_pieces=8)]
        locations = [make_location(location_id=1, total_deliveries=8)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.remaining_quantities[1] == 0

    def test_fixed_pieces_does_not_use_stove(self):
        """fixed_pieces breads should not appear in any stove session."""
        breads = [
            make_bread(
                bread_id=1, name="PreBaked", pieces_per_layer=[10], fixed_pieces=10
            ),
            make_bread(bread_id=2, name="Fresh", pieces_per_layer=[8]),
        ]
        locations = [make_location(location_id=1, total_deliveries=15)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        # Pre-baked bread should not appear in stove sessions
        for sess in result.plan.stove_sessions:
            for info in sess:
                if info is not None:
                    b_id, qty = info
                    assert b_id != 1, "fixed_pieces bread should not be in stove"

    def test_fixed_pieces_mixed_with_regular(self):
        """Mix of fixed_pieces and regular breads. Solver fills the gap."""
        breads = [
            make_bread(
                bread_id=1, name="PreBaked", pieces_per_layer=[10], fixed_pieces=6
            ),
            make_bread(bread_id=2, name="Fresh", pieces_per_layer=[8, 10]),
        ]
        locations = [make_location(location_id=1, total_deliveries=12)]
        caps = make_capacities(breads, locations, default_cap=12)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        # PreBaked: exactly 6, all distributed
        assert result.plan.bread_quantities[1] == 6
        assert result.plan.remaining_quantities[1] == 0
        # Fresh: makes up the rest
        assert result.plan.bread_quantities[2] >= 6

    def test_fixed_pieces_with_min_max_also_set(self):
        """When min == max on a regular bread, solver bakes exactly that amount."""
        breads = [
            make_bread(bread_id=1, pieces_per_layer=[10], min_pieces=10, max_pieces=10)
        ]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.bread_quantities[1] == 10


# ===========================================================================
# 2. Fingerprint / collector tests
# ===========================================================================


class TestSolutionFingerprint:
    """Tests for the deduplication fingerprint."""

    def test_identical_solutions_same_fingerprint(self):
        sol1 = {
            "stove_sessions": [[(1, 10), (2, 8), None, None]],
            "distribution": {(1, 1): 5, (2, 1): 3},
        }
        sol2 = {
            "stove_sessions": [[(1, 10), (2, 8), None, None]],
            "distribution": {(1, 1): 5, (2, 1): 3},
        }
        assert _solution_fingerprint(sol1) == _solution_fingerprint(sol2)

    def test_different_solutions_different_fingerprint(self):
        sol1 = {
            "stove_sessions": [[(1, 10), None, None, None]],
            "distribution": {(1, 1): 5},
        }
        sol2 = {
            "stove_sessions": [[(2, 8), None, None, None]],
            "distribution": {(2, 1): 5},
        }
        assert _solution_fingerprint(sol1) != _solution_fingerprint(sol2)

    def test_empty_solution(self):
        sol = {"stove_sessions": [], "distribution": {}}
        fp = _solution_fingerprint(sol)
        assert isinstance(fp, str)
        assert "###" in fp


# ===========================================================================
# 3. Model building tests
# ===========================================================================


class TestBuildModel:
    """Tests for model construction."""

    def test_model_builds_without_error(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        model, vars_dict = build_model(breads, locations, caps, max_sessions=3)

        assert model is not None
        assert "bread_ids" in vars_dict
        assert "layer" in vars_dict
        assert vars_dict["max_sessions"] == 3
        assert vars_dict["stove_layers"] == 4

    def test_model_custom_stove_layers(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        model, vars_dict = build_model(
            breads, locations, caps, max_sessions=3, stove_layers=6
        )

        assert vars_dict["stove_layers"] == 6


# ===========================================================================
# 4. Multiple solutions tests
# ===========================================================================


class TestMultipleSolutions:
    """Tests for multi-solution mode."""

    def test_solve_all_returns_list(self):
        breads = [
            make_bread(bread_id=1, name="Roggen", pieces_per_layer=[8, 10, 12]),
            make_bread(bread_id=2, name="Dinkel", pieces_per_layer=[6, 8]),
        ]
        locations = [make_location(location_id=1, total_deliveries=10)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning_all(
            breads,
            locations,
            caps,
            max_sessions=5,
            stove_layers=4,
            time_limit_seconds=10,
            max_solutions=5,
        )

        assert result is not None
        assert isinstance(result, dict)
        assert "solutions" in result
        assert "diagnostics" in result
        solutions = result["solutions"]
        assert isinstance(solutions, list)
        assert len(solutions) >= 1
        for sol in solutions:
            assert "bread_quantities" in sol
            assert "stove_sessions" in sol
            assert "distribution" in sol

    def test_solve_all_empty_input(self):
        result = solve_bread_planning_all([], [], {})
        assert result is not None
        assert isinstance(result, dict)
        assert "solutions" in result
        assert len(result["solutions"]) == 0


# ===========================================================================
# 5. Django integration tests
# ===========================================================================


class TestCollectSolverInput(TapirIntegrationTest):
    """Integration tests for collect_solver_input (requires DB)."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_collectSolverInput_noData_returnsNone(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        result = collect_solver_input(year=2099, delivery_week=1)

        self.assertIsNone(result)

    def test_collectSolverInput_withData_returnsCorrectStructure(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42

        bread1 = BreadFactory(
            name="Roggen",
            pieces_per_stove_layer=[10, 12],
            is_active=True,
            one_batch_can_be_baked_in_more_than_one_stove=False,
        )
        bread2 = BreadFactory(
            name="Dinkel",
            pieces_per_stove_layer=[8],
            is_active=True,
            one_batch_can_be_baked_in_more_than_one_stove=True,
        )

        loc = create_pickup_location_with_delivery_day(2, name="Markt")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread1
        )
        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread2
        )

        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc,
            bread=bread1,
            capacity=10,
        )
        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc,
            bread=bread2,
            capacity=10,
        )

        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc, bread=bread1
        )
        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc, bread=bread2
        )
        BreadDeliveryFactory(
            year=year, delivery_week=week, pickup_location=loc, bread=None
        )

        result = collect_solver_input(year=year, delivery_week=week, delivery_day=2)

        self.assertIsNotNone(result)
        self.assertIn("available_breads", result)
        self.assertIn("pickup_locations", result)
        self.assertIn("capacities", result)
        self.assertIn("stove_layers", result)

        self.assertEqual(len(result["available_breads"]), 2)
        self.assertEqual(len(result["pickup_locations"]), 1)
        self.assertEqual(result["pickup_locations"][0].total_deliveries, 3)

    def test_collectSolverInput_withData_fixedDemandReflectsDirectlyChosenBreads(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42

        bread1 = BreadFactory(
            name="Roggen",
            pieces_per_stove_layer=[10],
            is_active=True,
        )
        bread2 = BreadFactory(
            name="Dinkel",
            pieces_per_stove_layer=[8],
            is_active=True,
        )

        loc = create_pickup_location_with_delivery_day(2, name="Markt")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread1
        )
        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread2
        )

        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc,
            bread=bread1,
            capacity=10,
        )
        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc,
            bread=bread2,
            capacity=10,
        )

        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc, bread=bread1
        )
        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc, bread=bread2
        )
        BreadDeliveryFactory(
            year=year, delivery_week=week, pickup_location=loc, bread=None
        )

        result = collect_solver_input(year=year, delivery_week=week, delivery_day=2)

        self.assertIsNotNone(result)
        fixed = result["pickup_locations"][0].fixed_demand
        self.assertEqual(fixed.get(bread1.id, 0), 1)
        self.assertEqual(fixed.get(bread2.id, 0), 1)

    def test_collectSolverInput_specificsOverrideBreadDefaults(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 43

        bread = BreadFactory(
            name="Roggen",
            pieces_per_stove_layer=[10],
            is_active=True,
            min_pieces=5,
            max_pieces=50,
            min_remaining_pieces=2,
        )
        loc = create_pickup_location_with_delivery_day(3, name="TestLoc43")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=3, bread=bread
        )

        setup_bread_at_location(year, week, loc, bread)

        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc, bread=bread
        )

        BreadSpecificsPerDeliveryDayFactory(
            year=year,
            delivery_week=week,
            delivery_day=3,
            bread=bread,
            min_pieces=10,
            max_pieces=20,
            min_remaining_pieces=5,
            fixed_pieces=None,
        )

        result = collect_solver_input(year=year, delivery_week=week, delivery_day=3)

        self.assertIsNotNone(result)
        bread_info = result["available_breads"][0]
        self.assertEqual(bread_info.min_pieces, 10)
        self.assertEqual(bread_info.max_pieces, 20)
        self.assertEqual(bread_info.min_remaining_pieces, 5)

    def test_collectSolverInput_fixedPiecesSetOnBreadInfo(self):
        """When specifics set fixed_pieces, the BreadInfo should have fixed_pieces set."""
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 44

        bread = BreadFactory(
            name="Dinkel",
            pieces_per_stove_layer=[8],
            is_active=True,
            min_pieces=5,
            max_pieces=50,
        )
        loc = create_pickup_location_with_delivery_day(1, name="TestLoc44")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=1, bread=bread
        )

        setup_bread_at_location(year, week, loc, bread)

        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc, bread=bread
        )

        BreadSpecificsPerDeliveryDayFactory(
            year=year,
            delivery_week=week,
            delivery_day=1,
            bread=bread,
            fixed_pieces=15,
        )

        result = collect_solver_input(year=year, delivery_week=week, delivery_day=1)

        self.assertIsNotNone(result)
        bread_info = result["available_breads"][0]
        self.assertEqual(bread_info.fixed_pieces, 15)

    def test_collectSolverInput_differentDeliveryDay_returnsNone(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42

        bread = BreadFactory(
            name="Roggen",
            pieces_per_stove_layer=[10],
            is_active=True,
        )
        loc = create_pickup_location_with_delivery_day(2, name="Markt")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread
        )

        setup_bread_at_location(year, week, loc, bread)

        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc, bread=bread
        )
        # Query for day 5 but data is for day 2
        result = collect_solver_input(year=year, delivery_week=week, delivery_day=5)

        self.assertIsNone(result)

    def test_collectSolverInput_noDeliveryDayFilter_returnsAllDays(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42

        bread = BreadFactory(
            name="Roggen",
            pieces_per_stove_layer=[10],
            is_active=True,
        )
        loc_day2 = create_pickup_location_with_delivery_day(2, name="Tuesday")
        loc_day4 = create_pickup_location_with_delivery_day(4, name="Thursday")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread
        )
        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=4, bread=bread
        )

        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc_day2,
            bread=bread,
            capacity=10,
        )
        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc_day4,
            bread=bread,
            capacity=10,
        )

        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc_day2, bread=bread
        )
        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc_day4, bread=bread
        )

        result = collect_solver_input(year=year, delivery_week=week)

        self.assertIsNotNone(result)
        self.assertEqual(len(result["pickup_locations"]), 2)

    def test_collectSolverInput_multipleLocations_correctDeliveryCounts(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42

        bread = BreadFactory(
            name="Roggen",
            pieces_per_stove_layer=[10],
            is_active=True,
        )
        loc1 = create_pickup_location_with_delivery_day(2, name="Markt")
        loc2 = create_pickup_location_with_delivery_day(2, name="Hof")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread
        )

        for _ in range(3):
            BreadDeliveryFactory(
                year=year, delivery_week=week, pickup_location=loc1, bread=None
            )
        for _ in range(2):
            BreadDeliveryFactory(
                year=year, delivery_week=week, pickup_location=loc2, bread=None
            )

        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc1,
            bread=bread,
            capacity=10,
        )
        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc2,
            bread=bread,
            capacity=10,
        )

        result = collect_solver_input(year=year, delivery_week=week, delivery_day=2)

        self.assertIsNotNone(result)
        self.assertEqual(len(result["pickup_locations"]), 2)

        delivery_counts = {
            loc.name: loc.total_deliveries for loc in result["pickup_locations"]
        }
        self.assertEqual(delivery_counts["Markt"], 3)
        self.assertEqual(delivery_counts["Hof"], 2)

    def test_collectSolverInput_breadCanSpanSessions_mappedCorrectly(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42

        bread_span = BreadFactory(
            name="SpanBread",
            pieces_per_stove_layer=[10],
            is_active=True,
            one_batch_can_be_baked_in_more_than_one_stove=True,
        )
        bread_no_span = BreadFactory(
            name="NoSpanBread",
            pieces_per_stove_layer=[10],
            is_active=True,
            one_batch_can_be_baked_in_more_than_one_stove=False,
        )

        loc = create_pickup_location_with_delivery_day(2, name="Markt")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread_span
        )
        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread_no_span
        )

        BreadDeliveryFactory(
            year=year, delivery_week=week, pickup_location=loc, bread=None
        )

        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc,
            bread=bread_span,
            capacity=10,
        )
        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc,
            bread=bread_no_span,
            capacity=10,
        )

        result = collect_solver_input(year=year, delivery_week=week, delivery_day=2)

        self.assertIsNotNone(result)
        bread_map = {b.name: b for b in result["available_breads"]}
        self.assertTrue(bread_map["SpanBread"].can_span_sessions)
        self.assertFalse(bread_map["NoSpanBread"].can_span_sessions)


class TestSaveSolutionToDb(TapirIntegrationTest):
    """Integration tests for save_solution_to_db."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_saveSolutionToDb_savesDistributionAndSessions(self):
        from tapir.bakery.models import BreadsPerPickupLocationPerWeek, StoveSession
        from tapir.bakery.solver.django_integration import save_solution_to_db

        year = 2026
        week = 45
        delivery_day = 2

        bread1 = BreadFactory()
        bread2 = BreadFactory()
        loc = create_pickup_location_with_delivery_day(delivery_day, name="SaveTest")

        solution = {
            "bread_quantities": {bread1.id: 10, bread2.id: 8},
            "remaining_quantities": {bread1.id: 2, bread2.id: 0},
            "stove_sessions": [
                [(bread1.id, 10), (bread2.id, 8), None, None],
            ],
            "distribution": {
                (bread1.id, loc.id): 8,
                (bread2.id, loc.id): 8,
            },
        }

        save_solution_to_db(year, week, delivery_day, solution)

        dist_records = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year, delivery_week=week
        )
        self.assertEqual(dist_records.count(), 2)

        sess_records = StoveSession.objects.filter(year=year, delivery_week=week)
        self.assertEqual(sess_records.count(), 2)

    def test_saveSolutionToDb_calledTwice_replacesExistingRecords(self):
        """save_solution_to_db deletes previous records for the same locations before inserting."""
        from tapir.bakery.models import BreadsPerPickupLocationPerWeek
        from tapir.bakery.solver.django_integration import save_solution_to_db

        year = 2026
        week = 46
        delivery_day = 3

        bread = BreadFactory()
        loc = create_pickup_location_with_delivery_day(
            delivery_day, name="OverwriteTest"
        )

        solution = {
            "bread_quantities": {bread.id: 10},
            "remaining_quantities": {bread.id: 2},
            "stove_sessions": [[(bread.id, 10), None, None, None]],
            "distribution": {(bread.id, loc.id): 8},
        }

        save_solution_to_db(year, week, delivery_day, solution)
        self.assertEqual(
            BreadsPerPickupLocationPerWeek.objects.filter(
                year=year, delivery_week=week
            ).count(),
            1,
        )

        # Second call should replace, not append
        save_solution_to_db(year, week, delivery_day, solution)
        self.assertEqual(
            BreadsPerPickupLocationPerWeek.objects.filter(
                year=year, delivery_week=week
            ).count(),
            1,  # Still 1, not 2
        )

    def test_saveSolutionToDb_emptyDistribution_noRecordsCreated(self):
        from tapir.bakery.models import BreadsPerPickupLocationPerWeek
        from tapir.bakery.solver.django_integration import save_solution_to_db

        year = 2026
        week = 48
        delivery_day = 2

        bread = BreadFactory()

        solution = {
            "bread_quantities": {bread.id: 10},
            "remaining_quantities": {bread.id: 10},
            "stove_sessions": [[(bread.id, 10), None, None, None]],
            "distribution": {},
        }

        save_solution_to_db(year, week, delivery_day, solution)

        dist_records = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year, delivery_week=week
        )
        self.assertEqual(dist_records.count(), 0)

    def test_saveSolutionToDb_multipleSessionsWithNoneLayers_savedCorrectly(self):
        from tapir.bakery.models import StoveSession
        from tapir.bakery.solver.django_integration import save_solution_to_db

        year = 2026
        week = 49
        delivery_day = 2

        bread = BreadFactory()
        loc = create_pickup_location_with_delivery_day(
            delivery_day, name="MultiSession"
        )

        solution = {
            "bread_quantities": {bread.id: 20},
            "remaining_quantities": {bread.id: 4},
            "stove_sessions": [
                [(bread.id, 10), None, None, None],
                [(bread.id, 10), None, None, None],
            ],
            "distribution": {(bread.id, loc.id): 16},
        }

        save_solution_to_db(year, week, delivery_day, solution)

        sess_records = StoveSession.objects.filter(
            year=year, delivery_week=week
        ).order_by("session_number", "layer_number")
        self.assertEqual(sess_records.count(), 2)


class TestSolveAndSave(TapirIntegrationTest):
    """End-to-end test: collect → solve → save."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_solveAndSave_fullPipeline_savesResults(self):
        from tapir.bakery.models import BreadsPerPickupLocationPerWeek, StoveSession
        from tapir.bakery.solver.django_integration import solve_and_save

        year = 2026
        week = 47

        bread = BreadFactory(
            name="Testbrot",
            pieces_per_stove_layer=[10],
            is_active=True,
        )
        loc = create_pickup_location_with_delivery_day(2, name="PipelineTest")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread
        )

        BreadCapacityPickupLocationFactory(
            year=year,
            delivery_week=week,
            pickup_location=loc,
            bread=bread,
            capacity=10,
        )

        for _ in range(5):
            BreadDeliveryFactory(
                year=year, delivery_week=week, pickup_location=loc, bread=None
            )

        result = solve_and_save(year=year, delivery_week=week, delivery_day=2)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, SolverResult)
        self.assertEqual(result.status, "optimal")
        self.assertIsNotNone(result.plan)
        self.assertEqual(result.plan.total_deliveries, 5)
        self.assertGreaterEqual(result.plan.sessions_used, 1)

        self.assertTrue(
            BreadsPerPickupLocationPerWeek.objects.filter(
                year=year, delivery_week=week
            ).exists()
        )
        self.assertTrue(
            StoveSession.objects.filter(year=year, delivery_week=week).exists()
        )

    def test_solveAndSave_noData_returnsNone(self):
        from tapir.bakery.solver.django_integration import solve_and_save

        result = solve_and_save(year=2099, delivery_week=1, delivery_day=1)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, SolverResult)
        self.assertEqual(result.status, "no_data")
        self.assertIsNone(result.plan)
