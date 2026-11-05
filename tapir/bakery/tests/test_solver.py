import random
from collections import defaultdict
from decimal import Decimal
from unittest.mock import patch

import pytest

# ortools is the optional "bakery" extra, and every import below reaches it.
pytest.importorskip(
    "ortools",
    reason="ortools is not installed; run poetry install --extras bakery",
)

from django.db import connection
from django.test.utils import CaptureQueriesContext

from tapir.bakery.models import BreadDelivery, PreferredBread
from tapir.bakery.solver.collector import _solution_fingerprint
from tapir.bakery.solver.dataclasses import (
    BreadInfo,
    PickupLocationInfo,
    SolverResult,
)
from tapir.bakery.solver.solve import (
    PREVIEW_TIME_LIMIT_SECONDS,
    solve_bread_planning,
    solve_bread_planning_all,
)
from tapir.bakery.solver.solver_model import build_model
from tapir.bakery.tests.factories import (
    AvailableBreadsForDeliveryDayFactory,
    BreadCapacityPickupLocationFactory,
    BreadDeliveryFactory,
    BreadFactory,
    BreadGroupFactory,
    BreadSpecificsPerDeliveryDayFactory,
    BreadSubscriptionFactory,
)
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

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
    group=None,
    group_min=None,
    group_max=None,
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
        group_id=group,
        group_name=group,
        group_min_pieces=group_min,
        group_max_pieces=group_max,
    )


def make_location(location_id=1, name="Markt", total_deliveries=5, fixed_demand=None):
    return PickupLocationInfo(
        location_id=location_id,
        name=name,
        total_deliveries=total_deliveries,
        fixed_demand=fixed_demand or {},
    )


def make_capacities(breads, locations, default_cap=None):
    caps = {}
    for b in breads:
        for loc in locations:
            cap = default_cap if default_cap is not None else loc.total_deliveries
            caps[(b.bread_id, loc.location_id)] = cap
    return caps


def assert_solver_success(result):
    assert result is not None
    assert isinstance(result, SolverResult)
    assert (
        result.status == "optimal"
    ), f"Expected status 'ok', got '{result.status}': {result.diagnostics}"
    assert result.plan is not None


def assert_solver_failed(result):
    assert result is not None
    assert isinstance(result, SolverResult)
    assert result.status != "optimal"
    assert result.plan is None


def setup_bread_at_location(year, week, loc, bread, capacity=10):
    BreadCapacityPickupLocationFactory(
        year=year,
        delivery_week=week,
        pickup_location=loc,
        bread=bread,
        capacity=capacity,
    )


def create_bread_delivery_without_validation(year, week, pickup_location, bread=None):
    """
    BreadDelivery.clean() validates availability through several related
    models, which these tests set up themselves.
    """

    with patch.object(BreadDelivery, "clean", return_value=None):
        return BreadDeliveryFactory(
            year=year,
            delivery_week=week,
            pickup_location=pickup_location,
            bread=bread,
        )


class TestSolverBasic:
    def test_single_bread_single_location(self):
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
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], min_pieces=20)]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.bread_quantities[1] >= 20

    def test_respects_max_pieces(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], max_pieces=10)]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.bread_quantities[1] <= 10

    def test_respects_min_remaining(self):
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
        locations = [make_location()]
        result = solve_bread_planning([], locations, {})
        assert_solver_failed(result)
        assert result.status == "no_data"

    def test_empty_locations_returns_no_data(self):
        breads = [make_bread()]
        result = solve_bread_planning(breads, [], {})
        assert_solver_failed(result)
        assert result.status == "no_data"

    def test_capacityBelowWhatMembersAlreadyChose_isInfeasibleWithTheReason(self):
        # With lb > ub on an int var, CP-SAT answers MODEL_INVALID rather than
        # INFEASIBLE.
        breads = [make_bread(bread_id=1, name="Roggenbrot")]
        locations = [
            make_location(
                location_id=1, name="Hofladen", total_deliveries=5, fixed_demand={1: 5}
            )
        ]

        result = solve_bread_planning(breads, locations, {(1, 1): 2})

        assert_solver_failed(result)
        assert result.status == "infeasible"
        reasons = [
            d
            for d in result.diagnostics
            if d.category == "fixed_demand_exceeds_capacity"
        ]
        assert len(reasons) == 1
        assert "Roggenbrot" in reasons[0].message
        assert "Zeitlimit" not in " ".join(d.message for d in result.diagnostics)

    def test_empty_pieces_per_layer_returns_no_data(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[])]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        assert breads[0].pieces_per_stove_layer == []

        result = solve_bread_planning(breads, locations, caps)
        assert_solver_failed(result)
        assert result.status == "no_data"


class TestSolverMultipleBreads:
    def test_two_breads_one_location(self):
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
    def test_no_span_single_session(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], can_span=False)]
        locations = [make_location(location_id=1, total_deliveries=8)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        sessions_with_bread = 0
        for sess in result.plan.stove_sessions:
            if any(b_id == 1 for layer in sess for b_id, _ in layer):
                sessions_with_bread += 1
        assert sessions_with_bread <= 1

    def test_can_span_at_most_two_sessions(self):
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
            if any(b_id == 1 for layer in sess for b_id, _ in layer):
                sessions_with_bread += 1
        assert sessions_with_bread <= 2

    def test_cannot_span_three_sessions(self):
        # 20 pieces per session, so even a spanning bread tops out at 40.
        breads = [
            make_bread(
                bread_id=1,
                pieces_per_layer=[5],
                can_span=True,
                min_pieces=50,
            )
        ]
        locations = [make_location(location_id=1, total_deliveries=20)]
        caps = make_capacities(breads, locations, default_cap=50)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=10, stove_layers=4
        )

        assert_solver_failed(result)
        assert result.status == "infeasible"

    def test_layer_packing_no_gaps(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=15)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        for sess in result.plan.stove_sessions:
            last_used = -1
            for i, layer in enumerate(sess):
                if layer:
                    last_used = i
            for i in range(last_used):
                assert sess[
                    i
                ], f"Gap in layers: layer {i} is empty but layer {last_used} is used"

    def test_minimizes_sessions(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=8)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=10, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.sessions_used == 1

    def test_stove_layers_parameter(self):
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
    def test_different_qty_options(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[8, 10, 12])]
        locations = [make_location(location_id=1, total_deliveries=10)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        for sess in result.plan.stove_sessions:
            for layer in sess:
                for b_id, qty in layer:
                    assert qty in [8, 10, 12]


class TestCapacities:
    def test_capacity_limits_distribution(self):
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
    def test_total_distributed_equals_deliveries(self):
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
    def test_impossible_min_max_returns_error(self):
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
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = {(1, 1): 0}

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_failed(result)
        assert result.status == "infeasible"


class TestFixedPieces:
    def test_fixed_pieces_exact_quantity(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], fixed_pieces=10)]
        locations = [make_location(location_id=1, total_deliveries=10)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.bread_quantities[1] == 10

    def test_fixed_pieces_no_remaining(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[10], fixed_pieces=8)]
        locations = [make_location(location_id=1, total_deliveries=8)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.remaining_quantities[1] == 0

    def test_fixed_pieces_keeps_min_remaining(self):
        # Delivering all ten fixed pieces would save the stove session, but
        # three of them have to stay behind.
        breads = [
            make_bread(
                bread_id=1, pieces_per_layer=[10], fixed_pieces=10, min_remaining=3
            ),
            make_bread(bread_id=2, name="Dinkel", pieces_per_layer=[10]),
        ]
        locations = [make_location(location_id=1, total_deliveries=10)]
        caps = make_capacities(breads, locations)

        result = solve_bread_planning(
            breads, locations, caps, max_sessions=5, stove_layers=4
        )

        assert_solver_success(result)
        assert result.plan.remaining_quantities[1] >= 3
        assert result.plan.sessions_used == 1

    def test_fixed_pieces_does_not_use_stove(self):
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
        for sess in result.plan.stove_sessions:
            for layer in sess:
                for b_id, qty in layer:
                    assert b_id != 1

    def test_fixed_pieces_mixed_with_regular(self):
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
        assert result.plan.bread_quantities[1] == 6
        assert result.plan.bread_quantities[2] >= 6
        # Which bread carries the surplus is not asserted: both attributions
        # have the same objective, so the solver may return either.
        assert sum(result.plan.distribution.values()) == 12
        assert sum(result.plan.remaining_quantities.values()) == 2

    def test_fixed_pieces_with_min_max_also_set(self):
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


def layer_totals(plan):
    return [
        sum(qty for _, qty in layer)
        for session in plan.stove_sessions
        for layer in session
        if layer
    ]


class TestBreadGroups:
    """
    Breads of one group come from one dough: they may share a stove layer, and
    each one's own min/max ("Brot bearbeiten") bound the group's total, while
    its settings for the day ("Tageseinstellungen") bound only itself.
    """

    @staticmethod
    def _dough(group="Teig", min_pieces=12, max_pieces=48, pieces=([12], [12])):
        # min_pieces/max_pieces are the breads' own values, which bound the
        # group; without a group they are each bread's own limits.
        return [
            make_bread(
                bread_id=i + 1,
                name=name,
                pieces_per_layer=list(per_layer),
                group=group,
                group_min=min_pieces,
                group_max=max_pieces,
            )
            for i, (name, per_layer) in enumerate(zip("AB", pieces))
        ]

    @staticmethod
    def _solve(breads, locations):
        return solve_bread_planning(
            breads,
            locations,
            make_capacities(breads, locations),
            max_sessions=5,
            stove_layers=4,
        )

    def test_sixOfEach_shareOneLayer_althoughEachHasAMinimumOf12(self):
        # The example from the user story.
        breads = self._dough()
        locations = [
            make_location(total_deliveries=12, fixed_demand={1: 6, 2: 6}),
        ]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert result.plan.bread_quantities == {1: 6, 2: 6}
        assert result.plan.stove_sessions == [[[(1, 6), (2, 6)], [], [], []]]

    def test_withoutAGroup_eachBreadKeepsItsMinimumAndItsOwnLayer(self):
        breads = self._dough(group=None)
        locations = [
            make_location(total_deliveries=12, fixed_demand={1: 6, 2: 6}),
        ]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert result.plan.bread_quantities == {1: 12, 2: 12}
        assert all(
            len(layer) <= 1
            for session in result.plan.stove_sessions
            for layer in session
        )

    def test_groupTotal_staysWithinTheMaximum(self):
        # Max 48 each: alone each could reach 30, together they stop at 48.
        locations = [
            make_location(total_deliveries=60, fixed_demand={1: 30, 2: 30}),
        ]

        grouped = self._solve(self._dough(min_pieces=None), locations)
        ungrouped = self._solve(self._dough(group=None, min_pieces=None), locations)

        assert_solver_failed(grouped)
        assert "deliveries_exceed_production" in [
            d.category for d in grouped.diagnostics
        ]
        assert_solver_success(ungrouped)

    def test_groupTotal_reachesTheMaximumWithASharedLayer(self):
        breads = self._dough(min_pieces=None) + [
            make_bread(bread_id=3, name="C", pieces_per_layer=[12])
        ]
        locations = [
            make_location(total_deliveries=72, fixed_demand={1: 30, 2: 18}),
        ]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        quantities = result.plan.bread_quantities
        assert (quantities[1], quantities[2]) == (30, 18)
        assert quantities[3] >= 24

    def test_theLargestMinimumOfTheGroupCounts_andNotPerBread(self):
        breads = self._dough()
        breads[0].group_min_pieces = 24
        locations = [make_location(total_deliveries=12)]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert sum(result.plan.bread_quantities.values()) == 24

    def test_theSmallestMaximumOfTheGroupCounts(self):
        breads = self._dough(min_pieces=None)
        breads[1].group_max_pieces = 24
        locations = [
            make_location(total_deliveries=30, fixed_demand={1: 20, 2: 10}),
        ]

        result = self._solve(breads, locations)

        assert_solver_failed(result)

    def test_aSharedLayerHoldsACountEveryBreadOnItAllows(self):
        # 12 is the only count both allow: one shared layer of 12 wastes 2,
        # separate layers of 10 and 12 would waste 12.
        breads = self._dough(min_pieces=None, pieces=([10, 12], [12, 14]))
        locations = [
            make_location(total_deliveries=10, fixed_demand={1: 5, 2: 5}),
        ]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert layer_totals(result.plan) == [12]

    def test_layersAreOnlySharedWhenItHelps(self):
        breads = self._dough()
        locations = [
            make_location(total_deliveries=24, fixed_demand={1: 12, 2: 12}),
        ]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        used_layers = [
            layer
            for session in result.plan.stove_sessions
            for layer in session
            if layer
        ]
        assert sorted(used_layers) == [[(1, 12)], [(2, 12)]]

    def test_varietyAtOneStation_isNoReasonToShareALayer(self):
        # The story's limits without any choices: a second bread on the layer
        # would reach one more station, which is not worth a split loaf.
        breads = self._dough()
        locations = [make_location(total_deliveries=12)]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert sum(result.plan.bread_quantities.values()) == 12
        assert all(
            len(layer) <= 1
            for session in result.plan.stove_sessions
            for layer in session
        )

    def test_varietyAtExactlyFiveStations_isNoReasonToShareALayer(self):
        # 10 deliveries but a minimum of 12: the 2 left over are waste either
        # way, so only the variety at 5 stations speaks for sharing.
        breads = self._dough()
        locations = [
            make_location(location_id=i, name=f"Station{i}", total_deliveries=2)
            for i in range(5)
        ]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert all(
            len(layer) <= 1
            for session in result.plan.stove_sessions
            for layer in session
        )

    def test_varietyAtMoreThanFiveStations_isAReasonToShareALayer(self):
        # Every one of the 6 stations gets both breads instead of one.
        breads = self._dough()
        locations = [
            make_location(location_id=i, name=f"Station{i}", total_deliveries=2)
            for i in range(6)
        ]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert result.plan.stove_sessions == [[[(1, 6), (2, 6)], [], [], []]]

    def test_aMemberPreferringTheOtherBread_isAReasonToShareALayer(self):
        breads = self._dough()
        locations = [make_location(location_id=1, total_deliveries=12)]
        preferences = [
            {
                "member_id": m,
                "location_id": 1,
                "preferred_bread_ids": [2 if m == 0 else 1],
            }
            for m in range(12)
        ]

        result = solve_bread_planning(
            breads,
            locations,
            make_capacities(breads, locations),
            max_sessions=5,
            stove_layers=4,
            member_preferences=preferences,
        )

        assert_solver_success(result)
        assert result.plan.stove_sessions == [[[(1, 11), (2, 1)], [], [], []]]

    def test_breadsOfDifferentGroups_neverShareALayer(self):
        # 6 A and 6 C would fill one layer exactly, but A and C are in
        # different groups, so each needs a layer of 12.
        breads = self._dough(group="Roggen", min_pieces=None) + [
            make_bread(bread_id=3, name="C", pieces_per_layer=[12], group="Dinkel"),
            make_bread(bread_id=4, name="D", pieces_per_layer=[12], group="Dinkel"),
        ]
        locations = [
            make_location(total_deliveries=12, fixed_demand={1: 6, 3: 6}),
        ]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        groups = {1: "Roggen", 2: "Roggen", 3: "Dinkel", 4: "Dinkel"}
        for session in result.plan.stove_sessions:
            for layer in session:
                assert len({groups[b_id] for b_id, _ in layer}) <= 1
        assert layer_totals(result.plan) == [12, 12]

    def test_anUnbakedGroup_doesNotChangeHowTheRestOfThePlanIsScored(self):
        # Sharing is penalised on the group's own layers only: counting the
        # layers other breads hold would reward using more of them.
        bread_c = make_bread(bread_id=3, name="C", pieces_per_layer=[12])
        locations = [make_location(total_deliveries=12, fixed_demand={3: 12})]

        def best_objective(breads):
            output = solve_bread_planning_all(
                breads,
                locations,
                make_capacities(breads, locations),
                max_sessions=2,
                stove_layers=4,
                max_solutions=1,
            )
            # The plan's objective, as the first solve scores it.
            return round(output["solutions"][0]["objective"])

        assert best_objective(
            self._dough(min_pieces=None) + [bread_c]
        ) == best_objective([bread_c])

    def test_aDaySettingForOneBread_boundsOnlyThatBread(self):
        # The product owner's example: the group keeps Min 24 / Max 48, and
        # the day's settings ask for exactly 4 A. B fills up the group's
        # minimum and shares a layer with A.
        breads = self._dough(min_pieces=24)
        breads[0].min_pieces = breads[0].max_pieces = 4
        locations = [make_location(total_deliveries=24)]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert result.plan.bread_quantities == {1: 4, 2: 20}
        assert sorted(layer_totals(result.plan)) == [12, 12]

    def test_aBreadAloneInItsGroupThatDay_followsItsDaySetting(self):
        # Without a second bread that day there is no group, so as for an
        # ungrouped bread the day's setting replaces its own values.
        bread = self._dough(min_pieces=24)[0]
        bread.min_pieces = bread.max_pieces = 12
        locations = [make_location(total_deliveries=12)]

        result = self._solve([bread], locations)

        assert_solver_success(result)
        assert result.plan.bread_quantities == {1: 12}

    def test_aFixedAmount_countsTowardItsGroup_andSharesALayer(self):
        # Exactly 4 A as "Fixe Stück": A goes into the oven with its group,
        # and B fills up the group's minimum of 24.
        breads = self._dough(min_pieces=24)
        breads[0].fixed_pieces = 4
        locations = [make_location(total_deliveries=24)]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert result.plan.bread_quantities == {1: 4, 2: 20}
        assert sorted(layer_totals(result.plan)) == [12, 12]
        assert any(
            b_id == 1
            for session in result.plan.stove_sessions
            for layer in session
            for b_id, _ in layer
        )

    @staticmethod
    def _fixed_a_next_to_b(group_max):
        # A fits 12 per layer and B only 10, so no layer can hold both.
        return [
            make_bread(
                bread_id=1,
                name="A",
                pieces_per_layer=[12],
                fixed_pieces=5,
                group="Teig",
                group_max=group_max,
            ),
            make_bread(
                bread_id=2,
                name="B",
                pieces_per_layer=[10],
                group="Teig",
                group_max=group_max,
            ),
        ]

    def test_aFixedAmountThatCannotShareALayer_staysOutsideTheOven_butCounts(self):
        # A's 5 are baked outside the oven as before; with them, the group's
        # maximum of 15 leaves room for exactly one layer of B.
        breads = self._fixed_a_next_to_b(group_max=15)

        result = self._solve(breads, [make_location(total_deliveries=15)])

        assert_solver_success(result)
        assert result.plan.bread_quantities == {1: 5, 2: 10}
        assert result.plan.stove_sessions == [[[(2, 10)], [], [], []]]

    def test_aFixedAmountOutsideTheOven_isPartOfTheGroupMaximum(self):
        # With a maximum of 14, A's 5 leave no room for B's layer of 10.
        breads = self._fixed_a_next_to_b(group_max=14)

        result = self._solve(breads, [make_location(total_deliveries=15)])

        assert_solver_failed(result)
        assert "deliveries_exceed_production" in [
            d.category for d in result.diagnostics
        ]

    def test_whenEveryBreadOfAGroupIsFixed_theGroupsLimitsStillApply(self):
        # Fixed amounts count toward the group: 4 + 6 cannot reach its
        # minimum of 24, which the diagnostics say once and plainly.
        breads = self._dough(min_pieces=24)
        breads[0].fixed_pieces = 4
        breads[1].fixed_pieces = 6

        result = self._solve(breads, [make_location(total_deliveries=10)])

        assert_solver_failed(result)
        errors = [d.category for d in result.diagnostics if d.level == "error"]
        assert "group_day_limits_conflict" in errors
        assert "min_not_achievable" not in errors

    def test_aFixedAmountAloneInItsGroup_staysOutsideTheOven(self):
        # Without a second bread of the group that day, the fixed amount is
        # handled as for an ungrouped bread: it occupies no stove layer.
        bread = self._dough(min_pieces=24)[0]
        bread.fixed_pieces = 20
        locations = [make_location(total_deliveries=20)]

        result = self._solve([bread], locations)

        assert_solver_success(result)
        assert result.plan.bread_quantities == {1: 20}
        assert result.plan.stove_sessions == []

    def test_aFixedAmountWithoutCountsPerLayer_staysOutsideTheOven(self):
        breads = self._dough(min_pieces=None)
        breads[1].fixed_pieces = 20
        breads[1].pieces_per_stove_layer = []
        locations = [make_location(total_deliveries=32)]

        result = self._solve(breads, locations)

        assert_solver_success(result)
        assert result.plan.bread_quantities[2] == 20
        assert all(
            b_id != 2
            for session in result.plan.stove_sessions
            for layer in session
            for b_id, _ in layer
        )


class TestSolutionFingerprint:
    def test_identical_solutions_same_fingerprint(self):
        sol1 = {
            "stove_sessions": [[[(1, 10)], [(2, 8)], [], []]],
            "distribution": {(1, 1): 5, (2, 1): 3},
        }
        sol2 = {
            "stove_sessions": [[[(1, 10)], [(2, 8)], [], []]],
            "distribution": {(1, 1): 5, (2, 1): 3},
        }
        assert _solution_fingerprint(sol1) == _solution_fingerprint(sol2)

    def test_different_solutions_different_fingerprint(self):
        sol1 = {
            "stove_sessions": [[[(1, 10)], [], [], []]],
            "distribution": {(1, 1): 5},
        }
        sol2 = {
            "stove_sessions": [[[(2, 8)], [], [], []]],
            "distribution": {(2, 1): 5},
        }
        assert _solution_fingerprint(sol1) != _solution_fingerprint(sol2)

    def test_empty_solution(self):
        sol = {"stove_sessions": [], "distribution": {}}
        fp = _solution_fingerprint(sol)
        assert isinstance(fp, str)
        assert "###" in fp

    def test_sharedLayer_orderOfItsBreadsDoesNotMatter(self):
        sol1 = {"stove_sessions": [[[(1, 6), (2, 6)]]], "distribution": {}}
        sol2 = {"stove_sessions": [[[(2, 6), (1, 6)]]], "distribution": {}}
        assert _solution_fingerprint(sol1) == _solution_fingerprint(sol2)

    def test_sharedLayer_differsFromTheSameBreadsOnSeparateLayers(self):
        sol1 = {"stove_sessions": [[[(1, 6), (2, 6)], []]], "distribution": {}}
        sol2 = {"stove_sessions": [[[(1, 6)], [(2, 6)]]], "distribution": {}}
        assert _solution_fingerprint(sol1) != _solution_fingerprint(sol2)


class TestBuildModel:
    def test_model_builds_without_error(self):
        breads = [make_bread(bread_id=1, pieces_per_layer=[10])]
        locations = [make_location(location_id=1, total_deliveries=5)]
        caps = make_capacities(breads, locations)

        model, vars_dict = build_model(breads, locations, caps, max_sessions=3)

        assert model is not None
        assert "bread_ids" in vars_dict
        assert "pieces" in vars_dict
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


class TestMultipleSolutions:
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


class TestCollectSolverInput(TapirIntegrationTest):
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

        loc = create_pickup_location_with_opening_times([2], name="Markt")

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

        loc = create_pickup_location_with_opening_times([2], name="Markt")

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
        loc = create_pickup_location_with_opening_times([3], name="TestLoc43")

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
        loc = create_pickup_location_with_opening_times([1], name="TestLoc44")

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
        loc = create_pickup_location_with_opening_times([2], name="Markt")

        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=2, bread=bread
        )

        setup_bread_at_location(year, week, loc, bread)

        create_bread_delivery_without_validation(
            year=year, week=week, pickup_location=loc, bread=bread
        )
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
        loc_day2 = create_pickup_location_with_opening_times([2], name="Wednesday")
        loc_day4 = create_pickup_location_with_opening_times([4], name="Friday")

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

    def _bread_delivered_on_wednesday_and_friday(self, year, week):
        bread = BreadFactory(
            name="Roggen",
            pieces_per_stove_layer=[10],
            is_active=True,
            min_pieces=5,
            max_pieces=50,
            min_remaining_pieces=2,
        )
        for day in (2, 4):
            loc = create_pickup_location_with_opening_times([day], name=f"Day{day}")
            AvailableBreadsForDeliveryDayFactory(
                year=year, delivery_week=week, delivery_day=day, bread=bread
            )
            setup_bread_at_location(year, week, loc, bread)
            create_bread_delivery_without_validation(
                year=year, week=week, pickup_location=loc, bread=bread
            )
        return bread

    def test_collectSolverInput_wholeWeek_overridesOnSeveralDays_fallBackToBreadDefaults(
        self,
    ):
        from tapir.bakery.solver.django_integration import collect_solver_input

        bread = self._bread_delivered_on_wednesday_and_friday(2026, 44)
        for day, min_pieces in ((2, 10), (4, 30)):
            BreadSpecificsPerDeliveryDayFactory(
                year=2026,
                delivery_week=44,
                delivery_day=day,
                bread=bread,
                min_pieces=min_pieces,
                max_pieces=40,
                min_remaining_pieces=5,
                fixed_pieces=None,
            )

        with self.assertLogs(
            "tapir.bakery.solver.django_integration", level="WARNING"
        ) as logs:
            result = collect_solver_input(year=2026, delivery_week=44)

        bread_info = result["available_breads"][0]
        self.assertEqual(
            (
                bread_info.min_pieces,
                bread_info.max_pieces,
                bread_info.min_remaining_pieces,
            ),
            (5, 50, 2),
        )
        self.assertIn("several days", logs.output[0])

    def test_collectSolverInput_wholeWeek_overrideOnOneDay_isApplied(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        bread = self._bread_delivered_on_wednesday_and_friday(2026, 45)
        BreadSpecificsPerDeliveryDayFactory(
            year=2026,
            delivery_week=45,
            delivery_day=4,
            bread=bread,
            min_pieces=30,
            max_pieces=40,
            min_remaining_pieces=5,
            fixed_pieces=None,
        )

        result = collect_solver_input(year=2026, delivery_week=45)

        bread_info = result["available_breads"][0]
        self.assertEqual(
            (
                bread_info.min_pieces,
                bread_info.max_pieces,
                bread_info.min_remaining_pieces,
            ),
            (30, 40, 5),
        )

    def test_collectSolverInput_multipleLocations_correctDeliveryCounts(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42

        bread = BreadFactory(
            name="Roggen",
            pieces_per_stove_layer=[10],
            is_active=True,
        )
        loc1 = create_pickup_location_with_opening_times([2], name="Markt")
        loc2 = create_pickup_location_with_opening_times([2], name="Hof")

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

        loc = create_pickup_location_with_opening_times([2], name="Markt")

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

    def test_collectSolverInput_breadGroup_mappedCorrectly(self):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42

        group = BreadGroupFactory(name="Dinkelteig")
        grouped = BreadFactory(
            name="Dinkel hell", pieces_per_stove_layer=[12], group=group
        )
        ungrouped = BreadFactory(name="Roggen", pieces_per_stove_layer=[12])
        loc = create_pickup_location_with_opening_times([2], name="Markt")
        for bread in (grouped, ungrouped):
            AvailableBreadsForDeliveryDayFactory(
                year=year, delivery_week=week, delivery_day=2, bread=bread
            )
        BreadDeliveryFactory(
            year=year, delivery_week=week, pickup_location=loc, bread=None
        )

        result = collect_solver_input(year=year, delivery_week=week, delivery_day=2)

        bread_map = {b.name: b for b in result["available_breads"]}
        self.assertEqual(bread_map["Dinkel hell"].group_id, group.id)
        self.assertEqual(bread_map["Dinkel hell"].group_name, "Dinkelteig")
        self.assertIsNone(bread_map["Roggen"].group_id)
        self.assertIsNone(bread_map["Roggen"].group_name)

    def test_collectSolverInput_groupedBread_keepsItsDaySettingApartFromItsOwnValues(
        self,
    ):
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42
        group = BreadGroupFactory(name="Hell")
        helles, saaten = (
            BreadFactory(
                name=name,
                pieces_per_stove_layer=[12],
                min_pieces=24,
                max_pieces=48,
                group=group,
            )
            for name in ("Helles", "Helles mit Saaten")
        )
        loc = create_pickup_location_with_opening_times([2], name="Markt")
        for bread in (helles, saaten):
            AvailableBreadsForDeliveryDayFactory(
                year=year, delivery_week=week, delivery_day=2, bread=bread
            )
        BreadSpecificsPerDeliveryDayFactory(
            year=year,
            delivery_week=week,
            delivery_day=2,
            bread=helles,
            min_pieces=4,
            max_pieces=4,
            min_remaining_pieces=None,
            fixed_pieces=None,
        )
        BreadDeliveryFactory(
            year=year, delivery_week=week, pickup_location=loc, bread=None
        )

        result = collect_solver_input(year=year, delivery_week=week, delivery_day=2)

        limits = {
            b.name: (b.min_pieces, b.max_pieces, b.group_min_pieces, b.group_max_pieces)
            for b in result["available_breads"]
        }
        self.assertEqual(limits["Helles"], (4, 4, 24, 48))
        self.assertEqual(limits["Helles mit Saaten"], (None, None, 24, 48))

    def test_collectSolverInput_breadsComeSortedByName(self):
        # The solver lists a shared layer's breads in this order. Ids and
        # creation order both run against the names here.
        from tapir.bakery.solver.django_integration import collect_solver_input

        year = 2026
        week = 42
        loc = create_pickup_location_with_opening_times([2], name="Markt")
        for bread_id, name in (
            ("aaaaaaaaaa", "Zwiebelbrot"),
            ("zzzzzzzzzz", "Apfelbrot"),
        ):
            AvailableBreadsForDeliveryDayFactory(
                year=year,
                delivery_week=week,
                delivery_day=2,
                bread=BreadFactory(id=bread_id, name=name, pieces_per_stove_layer=[12]),
            )
        BreadDeliveryFactory(
            year=year, delivery_week=week, pickup_location=loc, bread=None
        )

        result = collect_solver_input(year=year, delivery_week=week, delivery_day=2)

        self.assertEqual(
            [b.name for b in result["available_breads"]], ["Apfelbrot", "Zwiebelbrot"]
        )


class TestSaveSolutionToDb(TapirIntegrationTest):
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
        loc = create_pickup_location_with_opening_times([delivery_day], name="SaveTest")

        solution = {
            "bread_quantities": {bread1.id: 10, bread2.id: 8},
            "remaining_quantities": {bread1.id: 2, bread2.id: 0},
            "stove_sessions": [
                [[(bread1.id, 10)], [(bread2.id, 8)], [], []],
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
        from tapir.bakery.models import BreadsPerPickupLocationPerWeek
        from tapir.bakery.solver.django_integration import save_solution_to_db

        year = 2026
        week = 46
        delivery_day = 3

        bread = BreadFactory()
        loc = create_pickup_location_with_opening_times(
            [delivery_day], name="OverwriteTest"
        )

        solution = {
            "bread_quantities": {bread.id: 10},
            "remaining_quantities": {bread.id: 2},
            "stove_sessions": [[[(bread.id, 10)], [], [], []]],
            "distribution": {(bread.id, loc.id): 8},
        }

        save_solution_to_db(year, week, delivery_day, solution)
        self.assertEqual(
            BreadsPerPickupLocationPerWeek.objects.filter(
                year=year, delivery_week=week
            ).count(),
            1,
        )

        save_solution_to_db(year, week, delivery_day, solution)
        self.assertEqual(
            BreadsPerPickupLocationPerWeek.objects.filter(
                year=year, delivery_week=week
            ).count(),
            1,
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
            "stove_sessions": [[[(bread.id, 10)], [], [], []]],
            "distribution": {},
        }

        save_solution_to_db(year, week, delivery_day, solution)

        dist_records = BreadsPerPickupLocationPerWeek.objects.filter(
            year=year, delivery_week=week
        )
        self.assertEqual(dist_records.count(), 0)

    def test_saveSolutionToDb_multipleSessionsWithEmptyLayers_savedCorrectly(self):
        from tapir.bakery.models import StoveSession
        from tapir.bakery.solver.django_integration import save_solution_to_db

        year = 2026
        week = 49
        delivery_day = 2

        bread = BreadFactory()
        loc = create_pickup_location_with_opening_times(
            [delivery_day], name="MultiSession"
        )

        solution = {
            "bread_quantities": {bread.id: 20},
            "remaining_quantities": {bread.id: 4},
            "stove_sessions": [
                [[(bread.id, 10)], [], [], []],
                [[(bread.id, 10)], [], [], []],
            ],
            "distribution": {(bread.id, loc.id): 16},
        }

        save_solution_to_db(year, week, delivery_day, solution)

        sess_records = StoveSession.objects.filter(
            year=year, delivery_week=week
        ).order_by("session_number", "layer_number")
        self.assertEqual(sess_records.count(), 2)

    def test_saveSolutionToDb_sharedLayer_savesARowPerBread(self):
        from tapir.bakery.models import StoveSession
        from tapir.bakery.solver.django_integration import save_solution_to_db

        year = 2026
        week = 50
        delivery_day = 2

        group = BreadGroupFactory()
        bread_a = BreadFactory(group=group)
        bread_b = BreadFactory(group=group)
        loc = create_pickup_location_with_opening_times(
            [delivery_day], name="SharedLayer"
        )

        solution = {
            "bread_quantities": {bread_a.id: 6, bread_b.id: 6},
            "remaining_quantities": {bread_a.id: 0, bread_b.id: 0},
            "stove_sessions": [[[(bread_a.id, 6), (bread_b.id, 6)], [], [], []]],
            "distribution": {(bread_a.id, loc.id): 6, (bread_b.id, loc.id): 6},
        }

        save_solution_to_db(year, week, delivery_day, solution)

        self.assertEqual(
            sorted(
                StoveSession.objects.filter(year=year, delivery_week=week).values_list(
                    "session_number", "layer_number", "bread_id", "quantity"
                )
            ),
            sorted([(1, 1, bread_a.id, 6), (1, 1, bread_b.id, 6)]),
        )


class TestMemberPreferences(TapirIntegrationTest):
    @staticmethod
    def _run(capacity_b, want_a=10, want_b=30):
        from ortools.sat.python import cp_model

        breads = [
            make_bread(bread_id=1, name="A", pieces_per_layer=[10]),
            make_bread(bread_id=2, name="B", pieces_per_layer=[10]),
        ]
        location = make_location(location_id=100, total_deliveries=want_a + want_b)
        capacities = {(1, 100): want_a + want_b, (2, 100): capacity_b}
        preferences = [
            {
                "member_id": m,
                "location_id": 100,
                "preferred_bread_ids": [1 if m < want_a else 2],
            }
            for m in range(want_a + want_b)
        ]
        model, v = build_model(
            breads,
            [location],
            capacities,
            max_sessions=8,
            stove_layers=4,
            member_preferences=preferences,
        )
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30
        solver.solve(model)
        return (
            {
                b.name: solver.value(v["distribution_vars"][b.bread_id, 100])
                for b in breads
            },
            sum(solver.value(x) for x in v["member_satisfied"].values()),
        )

    def test_distributionFollowsHowManyMembersWantEachBread(self):
        # The helper's defaults: 10 members want A, 30 want B.
        distribution, satisfied = self._run(capacity_b=40)

        self.assertEqual(distribution, {"A": 10, "B": 30})
        self.assertEqual(satisfied, 40)

    def test_satisfactionIsNotClaimedBeyondTheLoavesAvailable(self):
        # Only 10 loaves of B for the 30 members who want it, plus the 10 who
        # want A.
        _distribution, satisfied = self._run(capacity_b=10)

        self.assertEqual(satisfied, 20)


class TestSplittingVersusPreferences:
    """
    Splitting a bread over two stove sessions weighs as much as 100 members
    getting their favourite. Both setups need two sessions either way, and A
    only reaches the second half of the members if it is split.
    """

    @staticmethod
    def _everyone_wants_a(pieces_per_layer):
        members = 2 * 4 * pieces_per_layer
        breads = [
            make_bread(
                bread_id=1,
                name="A",
                pieces_per_layer=[pieces_per_layer],
                can_span=True,
            ),
            make_bread(bread_id=2, name="B", pieces_per_layer=[pieces_per_layer]),
        ]
        locations = [make_location(location_id=100, total_deliveries=members)]
        preferences = [
            {"member_id": m, "location_id": 100, "preferred_bread_ids": [1]}
            for m in range(members)
        ]

        result = solve_bread_planning(
            breads,
            locations,
            make_capacities(breads, locations),
            max_sessions=4,
            stove_layers=4,
            member_preferences=preferences,
        )

        assert_solver_success(result)
        sessions_with_a = sum(
            any(b_id == 1 for layer in session for b_id, _ in layer)
            for session in result.plan.stove_sessions
        )
        return result.plan, sessions_with_a

    def test_96MoreSatisfiedMembers_doNotJustifySplittingABread(self):
        plan, sessions_with_a = self._everyone_wants_a(pieces_per_layer=24)

        assert plan.sessions_used == 2
        assert sessions_with_a == 1
        assert plan.distribution[1, 100] == 96

    def test_104MoreSatisfiedMembers_justifySplittingABread(self):
        plan, sessions_with_a = self._everyone_wants_a(pieces_per_layer=26)

        assert plan.sessions_used == 2
        assert sessions_with_a == 2
        assert plan.distribution[1, 100] == 208


class TestGetMemberPreferences(TapirIntegrationTest):
    YEAR = 2026
    WEEK = 41
    DAY = 2

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.bread_a = BreadFactory.create(name="Roggenbrot")
        self.bread_b = BreadFactory.create(name="Dinkelkruste")
        self.location = create_pickup_location_with_opening_times(
            [self.DAY], name="Hofladen"
        )

    def _member_with_unassigned_delivery(self, favourites):
        member = MemberFactory.create()
        BreadDeliveryFactory(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=BreadSubscriptionFactory.create(member=member),
            pickup_location=self.location,
            bread=None,
        )
        if favourites is not None:
            preferred = PreferredBread.objects.create(member=member)
            preferred.breads.set(favourites)
        return member

    def test_returnsOneRowPerMemberAndLocation(self):
        from tapir.bakery.solver.preferences import get_member_preferences

        member = self._member_with_unassigned_delivery([self.bread_a, self.bread_b])

        result = get_member_preferences(self.YEAR, self.WEEK, self.DAY)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["member_id"], member.id)
        self.assertEqual(result[0]["location_id"], self.location.id)
        self.assertEqual(
            sorted(result[0]["preferred_bread_ids"]),
            sorted([self.bread_a.id, self.bread_b.id]),
        )

    def test_membersWithoutFavourites_areLeftOut(self):
        from tapir.bakery.solver.preferences import get_member_preferences

        self._member_with_unassigned_delivery(None)
        self._member_with_unassigned_delivery([])

        self.assertEqual(get_member_preferences(self.YEAR, self.WEEK, self.DAY), [])

    def test_readsThroughThePrefetchCache(self):
        # .values_list() on a prefetched related manager bypasses the prefetch
        # cache and fires one query per member.
        from tapir.bakery.solver.preferences import get_member_preferences

        for _ in range(2):
            self._member_with_unassigned_delivery([self.bread_a])
        with CaptureQueriesContext(connection) as two_members:
            get_member_preferences(self.YEAR, self.WEEK, self.DAY)

        for _ in range(2):
            self._member_with_unassigned_delivery([self.bread_a])
        with CaptureQueriesContext(connection) as four_members:
            get_member_preferences(self.YEAR, self.WEEK, self.DAY)

        self.assertEqual(
            len(four_members.captured_queries), len(two_members.captured_queries)
        )


class TestSolveAndSave(TapirIntegrationTest):
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
        loc = create_pickup_location_with_opening_times([2], name="PipelineTest")

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

    def _minimal_week(self, year, week, day=2, fixed_pieces=None):
        bread = BreadFactory(
            name="Testbrot", pieces_per_stove_layer=[10], is_active=True
        )
        loc = create_pickup_location_with_opening_times([day], name="FixedPiecesTest")
        AvailableBreadsForDeliveryDayFactory(
            year=year, delivery_week=week, delivery_day=day, bread=bread
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
        if fixed_pieces is not None:
            BreadSpecificsPerDeliveryDayFactory(
                year=year,
                delivery_week=week,
                delivery_day=day,
                bread=bread,
                fixed_pieces=fixed_pieces,
            )
        return bread

    def test_solveAndSave_persistsWhatToBake(self):
        from tapir.bakery.models import BreadsToBakePerWeek
        from tapir.bakery.solver.django_integration import solve_and_save

        year, week = 2026, 46
        bread = self._minimal_week(year, week)

        result = solve_and_save(year=year, delivery_week=week, delivery_day=2)

        row = BreadsToBakePerWeek.objects.get(
            year=year, delivery_week=week, bread=bread
        )
        self.assertEqual(row.quantity, result.plan.bread_quantities[bread.id])

    def test_solveAndSave_fixedPiecesBread_appearsOnTheBakingList(self):
        # A fixed_pieces bread occupies no stove layers.
        from tapir.bakery.services.baking_list_service import BakingListService
        from tapir.bakery.solver.django_integration import solve_and_save
        from tapir.bakery.models import StoveSession

        year, week = 2026, 45
        # More than the 5 deliveries the helper creates.
        bread = self._minimal_week(year, week, fixed_pieces=10)

        solve_and_save(year=year, delivery_week=week, delivery_day=2)

        self.assertFalse(
            StoveSession.objects.filter(
                year=year, delivery_week=week, bread=bread
            ).exists()
        )
        row = next(
            r
            for r in BakingListService.get_baking_list(year, week, 2)["breads"]
            if r["name"] == bread.name
        )
        self.assertEqual(row["baked"], 10)
        self.assertEqual(row["extra"], 5)

    def test_solveAndSave_wholeWeekWithoutADeliveryDay_saves(self):
        from tapir.bakery.models import BreadsToBakePerWeek, StoveSession
        from tapir.bakery.solver.django_integration import solve_and_save

        year, week = 2026, 44
        self._minimal_week(year, week)

        result = solve_and_save(year=year, delivery_week=week, delivery_day=None)

        self.assertEqual(result.status, "optimal")
        self.assertTrue(
            StoveSession.objects.filter(
                year=year, delivery_week=week, delivery_day__isnull=True
            ).exists()
        )
        self.assertTrue(
            BreadsToBakePerWeek.objects.filter(year=year, delivery_week=week).exists()
        )

    def test_solveAndSave_noData_returnsNone(self):
        from tapir.bakery.solver.django_integration import solve_and_save

        result = solve_and_save(year=2099, delivery_week=1, delivery_day=1)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, SolverResult)
        self.assertEqual(result.status, "no_data")
        self.assertIsNone(result.plan)

    def test_solveAndSave_logsPreferenceSatisfactionPerLocation(self):
        from tapir.bakery.models import PreferenceSatisfactionLogging
        from tapir.bakery.solver.django_integration import solve_and_save

        year, week, day = 2026, 43, 2
        self._minimal_week(year, week, day=day)

        solve_and_save(year=year, delivery_week=week, delivery_day=day)

        row = PreferenceSatisfactionLogging.objects.get(year=year, delivery_week=week)
        self.assertEqual(row.delivery_day, day)
        # Nobody set favourites, so everyone is happy with whatever they get.
        self.assertEqual(row.percentage_satisfied, Decimal("100.00"))

    def test_solveAndSave_runTwice_replacesTheSatisfactionLog(self):
        from tapir.bakery.models import PreferenceSatisfactionLogging
        from tapir.bakery.solver.django_integration import solve_and_save

        year, week, day = 2026, 42, 2
        self._minimal_week(year, week, day=day)

        solve_and_save(year=year, delivery_week=week, delivery_day=day)
        solve_and_save(year=year, delivery_week=week, delivery_day=day)

        self.assertEqual(
            PreferenceSatisfactionLogging.objects.filter(
                year=year, delivery_week=week
            ).count(),
            1,
        )


class TestSolutionCollector(TapirIntegrationTest):
    def test_maxSolutionsZero_stillReturnsThePlanItFound(self):
        breads = [make_bread(bread_id=1)]
        locations = [make_location(location_id=1, total_deliveries=5)]

        result = solve_bread_planning(
            breads, locations, make_capacities(breads, locations), max_solutions=0
        )

        assert_solver_success(result)


class TestAchievableQuantityDiagnostics(TapirIntegrationTest):
    """
    C10 caps a non-spanning bread at one stove session, C11 a spanning one at
    two.
    """

    @staticmethod
    def _diagnose(bread, location, capacities, max_sessions=8, stove_layers=4):
        from tapir.bakery.solver.diagnostics import diagnose_infeasibility

        return diagnose_infeasibility(
            [bread], [location], capacities, max_sessions, stove_layers
        )

    def test_minPiecesBeyondTheOvenCeiling_isReported(self):
        # One non-spanning bread, 10 per layer, 4 layers => at most 40 pieces,
        # so a min_pieces of 100 is impossible.
        bread = make_bread(bread_id=1, name="Roggenbrot", pieces_per_layer=[10])
        bread.min_pieces = 100
        location = make_location(location_id=1, total_deliveries=5)

        diagnostics = self._diagnose(bread, location, {(1, 1): 5})

        categories = [d.category for d in diagnostics]
        self.assertIn("min_not_achievable", categories)

    def test_minPiecesWithinTheOvenCeiling_isNotReported(self):
        bread = make_bread(bread_id=1, name="Roggenbrot", pieces_per_layer=[10])
        bread.min_pieces = 30
        location = make_location(location_id=1, total_deliveries=5)

        diagnostics = self._diagnose(bread, location, {(1, 1): 5})

        self.assertNotIn("min_not_achievable", [d.category for d in diagnostics])

    def test_spanningBreadGetsTwiceTheCeiling(self):
        # C11 allows a spanning bread two sessions, so 80 is reachable only
        # for it.
        location = make_location(location_id=1, total_deliveries=5)

        spanning = make_bread(
            bread_id=1, name="Sauerteig", pieces_per_layer=[10], can_span=True
        )
        spanning.min_pieces = 80
        non_spanning = make_bread(bread_id=1, name="Roggen", pieces_per_layer=[10])
        non_spanning.min_pieces = 80

        self.assertNotIn(
            "min_not_achievable",
            [d.category for d in self._diagnose(spanning, location, {(1, 1): 5})],
        )
        self.assertIn(
            "min_not_achievable",
            [d.category for d in self._diagnose(non_spanning, location, {(1, 1): 5})],
        )

    def test_fixedPiecesBread_isJudgedAgainstItsBatch_notTheOvenCeiling(self):
        # A fixed_pieces bread occupies no stove layers, so C10/C11 do not
        # apply to it.
        bread = make_bread(
            bread_id=1, name="Sauerteig", pieces_per_layer=[10], fixed_pieces=100
        )
        location = make_location(
            location_id=1, total_deliveries=60, fixed_demand={1: 60}
        )

        diagnostics = self._diagnose(bread, location, {(1, 1): 60})

        self.assertNotIn(
            "fixed_demand_exceeds_production", [d.category for d in diagnostics]
        )

    def test_fixedPiecesBread_demandAboveItsBatch_isStillReported(self):
        bread = make_bread(
            bread_id=1, name="Sauerteig", pieces_per_layer=[10], fixed_pieces=50
        )
        location = make_location(
            location_id=1, total_deliveries=60, fixed_demand={1: 60}
        )

        diagnostics = self._diagnose(bread, location, {(1, 1): 60})

        self.assertIn(
            "fixed_demand_exceeds_production", [d.category for d in diagnostics]
        )

    def test_directChoicesBeyondWhatCanBeBaked_isReported(self):
        # 60 members chose this bread directly, but the oven tops out at 40.
        bread = make_bread(bread_id=1, name="Roggenbrot", pieces_per_layer=[10])
        location = make_location(
            location_id=1, total_deliveries=60, fixed_demand={1: 60}
        )

        diagnostics = self._diagnose(bread, location, {(1, 1): 60})

        self.assertIn(
            "fixed_demand_exceeds_production", [d.category for d in diagnostics]
        )

    def test_maxPiecesAboveOneSession_nonSpanningBread_isCappedAtOneSession(self):
        # max_pieces says 96, but a non-spanning bread gets one session of
        # 4 layers à 12, so only 48 can go out.
        bread = make_bread(
            bread_id=1, name="Helles mit Saaten", pieces_per_layer=[12], max_pieces=96
        )
        location = make_location(location_id=1, total_deliveries=60)

        diagnostics = self._diagnose(bread, location, {(1, 1): 60})

        self.assertIn("deliveries_exceed_production", [d.category for d in diagnostics])

    def test_maxPiecesAboveOneSession_spanningBread_isNotReported(self):
        bread = make_bread(
            bread_id=1,
            name="Helles mit Saaten",
            pieces_per_layer=[12],
            can_span=True,
            max_pieces=96,
        )
        location = make_location(location_id=1, total_deliveries=60)

        diagnostics = self._diagnose(bread, location, {(1, 1): 60})

        self.assertNotIn(
            "deliveries_exceed_production", [d.category for d in diagnostics]
        )

    def test_fixedPiecesAllKeptAsRemaining_leavesNothingToDeliver(self):
        bread = make_bread(bread_id=1, name="Helles", fixed_pieces=20, min_remaining=20)
        location = make_location(location_id=1, total_deliveries=5)

        diagnostics = self._diagnose(bread, location, {(1, 1): 5})

        self.assertIn("deliveries_exceed_production", [d.category for d in diagnostics])

    def test_directChoicesAboveMaxPieces_isReported(self):
        # 12 per layer and max_pieces=20 leave a single layer of 12.
        bread = make_bread(
            bread_id=1, name="Saatenbrot", pieces_per_layer=[12], max_pieces=20
        )
        location = make_location(
            location_id=1, total_deliveries=15, fixed_demand={1: 15}
        )

        diagnostics = self._diagnose(bread, location, {(1, 1): 15})

        self.assertIn(
            "fixed_demand_exceeds_production", [d.category for d in diagnostics]
        )

    def test_directChoicesThatNeedTheLeftovers_isReported(self):
        # One session bakes at most 40, and 5 of them have to stay behind.
        bread = make_bread(
            bread_id=1, name="Saatenbrot", pieces_per_layer=[10], min_remaining=5
        )
        location = make_location(
            location_id=1, total_deliveries=38, fixed_demand={1: 38}
        )

        diagnostics = self._diagnose(bread, location, {(1, 1): 38})

        self.assertIn(
            "fixed_demand_exceeds_production", [d.category for d in diagnostics]
        )

    def test_maxPiecesBelowOneLayer_isWarnedEvenWithoutChoices(self):
        bread = make_bread(
            bread_id=1, name="Saatenbrot", pieces_per_layer=[10], max_pieces=5
        )
        location = make_location(location_id=1, total_deliveries=5)

        diagnostics = self._diagnose(bread, location, {(1, 1): 5})

        self.assertIn("max_below_one_layer", [d.category for d in diagnostics])

    def _shortfall_message(self, bread, location):
        diagnostics = self._diagnose(
            bread, location, {(1, 1): location.total_deliveries}
        )
        return next(
            d.message
            for d in diagnostics
            if d.category == "deliveries_exceed_production"
        )

    def test_splittingHint_whenTheOneSessionLimitHoldsTheBreadBack(self):
        bread = make_bread(
            bread_id=1, name="Helles mit Saaten", pieces_per_layer=[12], max_pieces=96
        )
        location = make_location(location_id=1, total_deliveries=60)

        self.assertIn("mehrere Ofengänge", self._shortfall_message(bread, location))

    def test_splittingHint_notWhenMaxPiecesIsTheLimit(self):
        # One session would hold 48, so splitting cannot lift the cap of 24.
        bread = make_bread(
            bread_id=1, name="Helles mit Saaten", pieces_per_layer=[12], max_pieces=24
        )
        location = make_location(location_id=1, total_deliveries=60)

        self.assertNotIn("mehrere Ofengänge", self._shortfall_message(bread, location))


class TestGroupDiagnostics:
    @staticmethod
    def _diagnose(breads, total_deliveries=12, fixed_demand=None):
        from tapir.bakery.solver.diagnostics import diagnose_infeasibility

        location = make_location(
            location_id=1, total_deliveries=total_deliveries, fixed_demand=fixed_demand
        )
        return diagnose_infeasibility(
            breads,
            [location],
            make_capacities(breads, [location]),
            max_sessions=8,
            stove_layers=4,
        )

    @staticmethod
    def _dough(limits, group="Teig"):
        return [
            make_bread(
                bread_id=i + 1,
                name=name,
                pieces_per_layer=[12],
                group=group,
                group_min=min_pieces,
                group_max=max_pieces,
            )
            for i, (name, (min_pieces, max_pieces)) in enumerate(zip("AB", limits))
        ]

    def test_largestMinimumAboveSmallestMaximum_isAConflict(self):
        diagnostics = self._diagnose(self._dough([(24, 48), (12, 12)]))

        conflict = next(
            d for d in diagnostics if d.category == "group_min_max_conflict"
        )
        assert conflict.level == "error"
        assert "Teig" in conflict.message

    def test_differingLimits_sayWhichOnesTheGroupUses(self):
        diagnostics = self._diagnose(self._dough([(12, 48), (24, 36)]))

        info = next(d for d in diagnostics if d.category == "group_limits")
        assert info.level == "info"
        assert "Min. 24 und Max. 36" in info.message

    def test_equalLimits_needNoExplanation(self):
        diagnostics = self._diagnose(self._dough([(12, 48), (12, 48)]))

        assert "group_limits" not in [d.category for d in diagnostics]

    def test_minimumOnlyTheGroupTogetherCanReach_isNotReported(self):
        # Neither bread can span sessions, so alone each tops out at 48.
        diagnostics = self._diagnose(self._dough([(60, None), (60, None)]))

        categories = [d.category for d in diagnostics]
        assert "min_not_achievable" not in categories
        assert "single_session_overflow" not in categories

    def test_minimumBeyondWhatTheGroupCanReach_isReported(self):
        diagnostics = self._diagnose(self._dough([(100, None), (100, None)]))

        error = next(d for d in diagnostics if d.category == "min_not_achievable")
        assert "Gruppe 'Teig'" in error.message

    def test_shortfall_countsTheGroupOnceWithinItsMaximum(self):
        diagnostics = self._diagnose(
            self._dough([(None, 48), (None, 48)]), total_deliveries=60
        )

        shortfall = next(
            d for d in diagnostics if d.category == "deliveries_exceed_production"
        )
        assert "Gruppe 'Teig': max gebacken=48" in shortfall.message

    def _with_c(self, fixed_demand, min_remaining=0):
        # C covers the deliveries the group cannot, so the overall shortfall
        # check stays quiet and only the group check can explain the result.
        breads = self._dough([(None, 48), (None, 48)]) + [
            make_bread(bread_id=3, name="C", pieces_per_layer=[12])
        ]
        for bread in breads[:2]:
            bread.min_remaining_pieces = min_remaining
        return self._diagnose(breads, total_deliveries=84, fixed_demand=fixed_demand)

    def test_directChoicesAboveTheGroupMaximum_areReported(self):
        diagnostics = self._with_c({1: 30, 2: 30})

        assert "deliveries_exceed_production" not in [d.category for d in diagnostics]
        error = next(
            d for d in diagnostics if d.category == "fixed_demand_exceeds_production"
        )
        assert "Gruppe 'Teig' ergibt zusammen 60 Stück" in error.message
        assert "höchstens 48" in error.message

    def test_directChoicesThatOnlyFitWithoutTheLeftovers_areReported(self):
        diagnostics = self._with_c({1: 24, 2: 20}, min_remaining=3)

        error = next(
            d for d in diagnostics if d.category == "fixed_demand_exceeds_production"
        )
        assert "plus mindestens 6 als Rest" in error.message

    def test_directChoicesWithinTheGroupMaximum_areNotReported(self):
        diagnostics = self._with_c({1: 24, 2: 24})

        assert "fixed_demand_exceeds_production" not in [
            d.category for d in diagnostics
        ]

    def test_directChoicesAboveWhatWholeLayersReach_areReported(self):
        # Max 50 each, but layers of 12 stop the group at 48.
        diagnostics = self._diagnose(
            self._dough([(None, 50), (None, 50)]),
            total_deliveries=49,
            fixed_demand={1: 25, 2: 24},
        )

        error = next(
            d for d in diagnostics if d.category == "fixed_demand_exceeds_production"
        )
        assert "höchstens 48 Stück backen (Max. 50)" in error.message

    def test_deliveriesAboveWhatWholeLayersReach_explainTheInfeasibleSolve(self):
        breads = self._dough([(None, 50), (None, 50)])
        locations = [make_location(total_deliveries=49)]

        result = solve_bread_planning(
            breads, locations, make_capacities(breads, locations), max_sessions=5
        )

        assert result.status == "infeasible"
        shortfall = next(
            d
            for d in result.diagnostics
            if d.category == "deliveries_exceed_production"
        )
        assert "Gruppe 'Teig': max gebacken=48" in shortfall.message

    def test_minimumAboveWhatWholeLayersReachUnderTheMaximum_isReported(self):
        # Layers of 12 under a maximum of 20 leave 12, below the minimum of 13.
        diagnostics = self._diagnose(self._dough([(13, 20), (13, 20)]))

        error = next(d for d in diagnostics if d.category == "min_not_achievable")
        assert "höchstens 12 Stück erreichbar" in error.message
        assert "group_min_max_conflict" not in [d.category for d in diagnostics]

    def test_minimumAboveMaximum_isOnlyReportedAsTheConflict(self):
        diagnostics = self._diagnose(self._dough([(24, 48), (12, 12)]))

        assert "min_not_achievable" not in [d.category for d in diagnostics]

    def test_equalMinAndMax_doesNotSuggestAFixedAmountForAGroupedBread(self):
        diagnostics = self._diagnose(self._dough([(12, 12), (12, 12)]))

        assert "min_max" not in [d.category for d in diagnostics]

    def test_daySettingsAskingForMoreThanTheGroupMaximum_areReported(self):
        breads = self._dough([(None, 48), (None, 48)])
        breads[0].min_pieces = breads[1].min_pieces = 30

        diagnostics = self._diagnose(breads, total_deliveries=48)

        error = next(
            d for d in diagnostics if d.category == "group_day_limits_conflict"
        )
        assert "mindestens 60 Stück" in error.message
        assert "höchstens 48 Stück" in error.message

    def test_aFixedAmountAboveTheGroupMaximum_isReported(self):
        breads = self._dough([(None, 48), (None, 48)])
        breads[0].fixed_pieces = 60

        diagnostics = self._diagnose(breads, total_deliveries=60)

        error = next(
            d for d in diagnostics if d.category == "group_day_limits_conflict"
        )
        assert "mindestens 60 Stück" in error.message

    def test_daySettingsAllowingLessThanTheGroupMinimum_areReported(self):
        breads = self._dough([(24, None), (24, None)])
        breads[0].max_pieces = 4
        breads[1].max_pieces = 10

        diagnostics = self._diagnose(breads)

        error = next(
            d for d in diagnostics if d.category == "group_day_limits_conflict"
        )
        assert "höchstens 14 Stück" in error.message
        assert "mindestens 24 Stück" in error.message

    def test_aDayMinimumBeyondWhatTheBreadReachesInItsGroup_isReported(self):
        # A does not span sessions: one session of 4 layers à 12 is its most.
        breads = self._dough([(None, None), (None, None)])
        breads[0].min_pieces = 60

        diagnostics = self._diagnose(breads, total_deliveries=60)

        error = next(
            d
            for d in diagnostics
            if d.category == "min_not_achievable" and d.bread_name == "A"
        )
        assert "Tageseinstellung Min. 60" in error.message
        assert "höchstens 48 Stück" in error.message

    def test_aDayAmountBelowOneLayer_isReportedWhenTheBreadCannotShare(self):
        # A fits 12 per layer and B only 10: no layer can hold both, so A's
        # 4 for the day cannot be baked.
        breads = [
            make_bread(
                bread_id=1,
                name="A",
                pieces_per_layer=[12],
                min_pieces=4,
                max_pieces=4,
                group="Teig",
            ),
            make_bread(bread_id=2, name="B", pieces_per_layer=[10], group="Teig"),
        ]

        diagnostics = self._diagnose(breads, total_deliveries=14)

        error = next(
            d
            for d in diagnostics
            if d.category == "min_not_achievable" and d.bread_name == "A"
        )
        assert "teilt mit keinem anderen Brot der Gruppe" in error.message
        assert "max_below_one_layer" in [
            d.category for d in diagnostics if d.bread_name == "A"
        ]

    def test_dayAmountsThatCannotFillASharedLayer_areReported(self):
        # 5 fixed A and at most 3 B never make a layer of 12.
        breads = self._dough([(None, None), (None, None)])
        breads[0].fixed_pieces = 5
        breads[1].max_pieces = 3

        diagnostics = self._diagnose(breads, total_deliveries=8)

        error = next(
            d
            for d in diagnostics
            if d.category == "min_not_achievable" and d.bread_name is None
        )
        assert "mindestens 5 Stück nach den Tageseinstellungen" in error.message
        assert "höchstens 0 Stück erreichbar" in error.message

    def test_exactlyFourOfOneBreadForTheDay_isNoProblemInItsGroup(self):
        # The product owner's example: 4 is less than a layer of 12, but A can
        # take part of a layer it shares with B.
        breads = self._dough([(24, 48), (24, 48)])
        breads[0].min_pieces = breads[0].max_pieces = 4

        diagnostics = self._diagnose(breads, total_deliveries=24)

        assert [d for d in diagnostics if d.level in ("error", "warning")] == []

    def test_groupMaximumBelowOneLayer_isWarnedForEachOfItsBreads(self):
        diagnostics = self._diagnose(self._dough([(None, 48), (None, 10)]))

        warnings = [d for d in diagnostics if d.category == "max_below_one_layer"]
        assert sorted(d.bread_name for d in warnings) == ["A", "B"]
        assert all(
            "Gruppe 'Teig' darf im Ofen höchstens 10" in d.message for d in warnings
        )

    def test_directChoicesAboveTheGroupMaximum_explainTheInfeasibleSolve(self):
        breads = self._dough([(None, 48), (None, 48)]) + [
            make_bread(bread_id=3, name="C", pieces_per_layer=[12])
        ]
        locations = [
            make_location(total_deliveries=84, fixed_demand={1: 30, 2: 30}),
        ]

        result = solve_bread_planning(
            breads, locations, make_capacities(breads, locations), max_sessions=5
        )

        assert result.status == "infeasible"
        assert "fixed_demand_exceeds_production" in [
            d.category for d in result.diagnostics
        ]


class TestEvenSpread:
    """
    Among plans that are otherwise equally good, the second solve picks the
    one that shares each station's loaves out most evenly.
    """

    @staticmethod
    def _breads():
        return [
            make_bread(bread_id=1, name="A", pieces_per_layer=[12], min_pieces=12),
            make_bread(bread_id=2, name="B", pieces_per_layer=[12], min_pieces=12),
        ]

    def _solve(self, locations, member_preferences=None):
        breads = self._breads()
        result = solve_bread_planning(
            breads,
            locations,
            make_capacities(breads, locations),
            max_sessions=5,
            stove_layers=4,
            member_preferences=member_preferences,
        )
        assert_solver_success(result)
        return result.plan

    @staticmethod
    def _two_stations():
        return [
            make_location(location_id=i, name=f"S{i}", total_deliveries=12)
            for i in (1, 2)
        ]

    def test_twoBreadsAtTwoStations_areSplitEvenly(self):
        # Variety alone is just as happy with 11 + 1 at each station.
        plan = self._solve(self._two_stations())

        assert plan.distribution == {(1, 1): 6, (2, 1): 6, (1, 2): 6, (2, 2): 6}

    def test_anEvenSpread_neverCostsAMemberTheirFavourite(self):
        # 10 members at S1 want A: they all get it, and only the rest of the
        # loaves are evened out.
        preferences = [
            {"member_id": m, "location_id": 1, "preferred_bread_ids": [1]}
            for m in range(10)
        ]

        plan = self._solve(self._two_stations(), member_preferences=preferences)

        assert plan.distribution == {(1, 1): 10, (2, 1): 2, (1, 2): 2, (2, 2): 10}

    def test_withoutTimeLeftForTheSpread_theFirstPlanIsReturned(self):
        with patch("tapir.bakery.solver.solve.SPREAD_TIME_LIMIT_SECONDS", 0):
            plan = self._solve(self._two_stations())

        assert plan.bread_quantities == {1: 12, 2: 12}
        assert sum(plan.distribution.values()) == 24

    def test_theSpreadKeepsThePlansObjective(self):
        breads = self._breads()
        locations = self._two_stations()

        def best_objective(spread_seconds):
            with patch(
                "tapir.bakery.solver.solve.SPREAD_TIME_LIMIT_SECONDS", spread_seconds
            ):
                output = solve_bread_planning_all(
                    breads,
                    locations,
                    make_capacities(breads, locations),
                    max_sessions=5,
                    stove_layers=4,
                    max_solutions=1,
                )
            return output["solutions"][0]["objective"]

        assert best_objective(5) == best_objective(0)


class TestRealisticWeek:
    """
    A mid-sized week: 8 breads, 10 stations, 300 members with one to three
    favourites each. It solves to optimality in a few seconds, well within the
    time the solver preview view allows, also with two pairs of breads grouped.
    """

    PIECES_PER_LAYER = [
        [10, 11, 12],
        [12, 14],
        [10, 12],
        [8, 9],
        [12, 14, 16],
        [16, 18],
        [10, 12],
        [12, 14],
    ]

    # Each pair shares 12 pieces per layer as the only count both allow.
    GROUPS = {2: "Teig1", 3: "Teig1", 7: "Teig2", 8: "Teig2"}
    GROUP_MAX_PIECES = 48

    def _week(self, groups):
        rng = random.Random(0)
        breads = [
            make_bread(
                bread_id=i + 1,
                name=f"Brot{i + 1}",
                pieces_per_layer=pieces_per_layer,
                can_span=i % 3 == 0,
                min_remaining=2,
                group=groups.get(i + 1),
                group_max=self.GROUP_MAX_PIECES if i + 1 in groups else None,
            )
            for i, pieces_per_layer in enumerate(self.PIECES_PER_LAYER)
        ]
        locations = [
            make_location(location_id=100 + j, name=f"Station{j}", total_deliveries=30)
            for j in range(10)
        ]
        capacities = make_capacities(breads, locations, default_cap=15)
        preferences = []
        for loc in locations:
            for _ in range(loc.total_deliveries):
                preferences.append(
                    {
                        "member_id": len(preferences),
                        "location_id": loc.location_id,
                        "preferred_bread_ids": rng.sample(
                            [b.bread_id for b in breads], k=rng.randint(1, 3)
                        ),
                    }
                )
        return breads, locations, capacities, preferences

    def test_realisticWeek_isSolvedToOptimalityWithinTheViewsTimeLimit(self):
        self._solve_and_check(groups={})

    def test_realisticWeekWithGroups_isSolvedToOptimalityWithinTheViewsTimeLimit(
        self,
    ):
        plan = self._solve_and_check(groups=self.GROUPS)

        options_by_bread = dict(enumerate(self.PIECES_PER_LAYER, start=1))
        for session in plan.stove_sessions:
            for layer in session:
                assert len({self.GROUPS.get(b_id, b_id) for b_id, _ in layer}) <= 1
                total = sum(qty for _, qty in layer)
                assert all(total in options_by_bread[b_id] for b_id, _ in layer)
        for group in set(self.GROUPS.values()):
            assert (
                sum(
                    plan.bread_quantities[b_id]
                    for b_id, b_group in self.GROUPS.items()
                    if b_group == group
                )
                <= self.GROUP_MAX_PIECES
            )

    def _solve_and_check(self, groups):
        breads, locations, capacities, preferences = self._week(groups)

        result = solve_bread_planning(
            breads,
            locations,
            capacities,
            max_sessions=10,
            stove_layers=4,
            time_limit_seconds=PREVIEW_TIME_LIMIT_SECONDS,
            member_preferences=preferences,
        )

        assert_solver_success(result)
        plan = result.plan
        for loc in locations:
            delivered = sum(
                plan.distribution.get((b.bread_id, loc.location_id), 0) for b in breads
            )
            assert delivered == loc.total_deliveries
        for key, count in plan.distribution.items():
            assert count <= capacities[key]

        baked_in_oven = defaultdict(int)
        sessions_per_bread = defaultdict(set)
        for index, session in enumerate(plan.stove_sessions):
            for layer in session:
                for bread_id, pieces in layer:
                    baked_in_oven[bread_id] += pieces
                    sessions_per_bread[bread_id].add(index)
        for b in breads:
            baked = plan.bread_quantities[b.bread_id]
            remaining = plan.remaining_quantities[b.bread_id]
            distributed = sum(
                plan.distribution.get((b.bread_id, loc.location_id), 0)
                for loc in locations
            )
            assert baked == baked_in_oven[b.bread_id] == distributed + remaining
            if baked:
                assert remaining >= b.min_remaining_pieces
            assert len(sessions_per_bread[b.bread_id]) <= (
                2 if b.can_span_sessions else 1
            )
        return plan
