import datetime
from unittest.mock import patch

from tapir.bakery.services.distribution_list_service import DistributionListService
from tapir.bakery.tests.factories import (
    BreadDeliveryFactory,
    BreadFactory,
    BreadSubscriptionFactory,
    BreadsPerPickupLocationPerWeekFactory,
)
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak


@patch("tapir.wirgarten.tests.factories.KeycloakUserManager.get_keycloak_client")
class TestDistributionListService(TapirIntegrationTest):
    YEAR = 2026
    WEEK = 11
    DAY = 3

    @classmethod
    def setUpTestData(cls):
        # The station a slot belongs to is derived, and resolving it needs the
        # org delivery weekday parameter.
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        set_bypass_keycloak()
        self.roggenbrot = BreadFactory.create(name="Roggenbrot")
        self.dinkelkruste = BreadFactory.create(name="Dinkelkruste")

    def _make_subscription(self):
        # A member belongs to one station per week, so every delivery placed at
        # a different station needs its own member.
        return BreadSubscriptionFactory.create(member=MemberFactory.create())

    def _run_with_locations(self, locations):
        """
        Run get_distribution_list for stations delivered on self.DAY.

        Real opening times rather than a patched queryset: which stations
        deliver on a day is one shared rule now, so a test that mocks the
        query stops exercising it.
        """
        for pickup_location in locations:
            PickupLocationOpeningTime.objects.get_or_create(
                pickup_location=pickup_location,
                day_of_week=self.DAY,
                defaults={
                    "open_time": datetime.time(8),
                    "close_time": datetime.time(18),
                },
            )
        return DistributionListService.get_distribution_list(
            year=self.YEAR, week=self.WEEK, day=self.DAY
        )

    # ══════════════════════════════════════════════════════════════════
    # NO DATA
    # ══════════════════════════════════════════════════════════════════

    def test_getDistributionList_noData_returnsEmptyResult(self, mock_kc):
        result = DistributionListService.get_distribution_list(
            year=self.YEAR, week=self.WEEK, day=self.DAY
        )

        self.assertFalse(result["has_solver_results"])
        self.assertEqual(result["locations"], [])
        self.assertEqual(result["bread_names"], [])
        self.assertEqual(result["bread_totals"], {})
        self.assertEqual(result["grand_total_baked"], 0)
        self.assertEqual(result["grand_total_ordered"], 0)
        self.assertEqual(result["grand_total_extra"], 0)

    # ══════════════════════════════════════════════════════════════════
    # WITHOUT SOLVER RESULTS (no BreadsPerPickupLocationPerWeek)
    # ══════════════════════════════════════════════════════════════════

    # ── Without solver: deliveries with bread assigned ───────────────

    def test_withoutSolver_deliveriesWithBread_showsOrderedCounts(self, mock_kc):
        pl = PickupLocationFactory.create(name="Hofladen")
        sub = self._make_subscription()

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=self.roggenbrot,
        )

        result = self._run_with_locations([pl])

        self.assertFalse(result["has_solver_results"])
        self.assertEqual(len(result["locations"]), 1)

        loc = result["locations"][0]
        self.assertEqual(loc["name"], "Hofladen")
        self.assertEqual(loc["breads"]["Roggenbrot"]["ordered"], 1)
        self.assertEqual(loc["total_ordered"], 1)
        self.assertEqual(loc["total_baked"], 1)  # total deliveries
        self.assertEqual(loc["total_extra"], 0)

    # ── Without solver: delivery without bread (unassigned slot) ─────

    def test_withoutSolver_deliveryWithoutBread_countsAsTotalButNotOrdered(
        self, mock_kc
    ):
        pl = PickupLocationFactory.create(name="Hofladen")
        sub = self._make_subscription()

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=None,
        )

        result = self._run_with_locations([pl])

        self.assertFalse(result["has_solver_results"])
        loc = result["locations"][0]
        self.assertEqual(loc["total_baked"], 1)  # 1 delivery total
        self.assertEqual(loc["total_ordered"], 0)  # no bread assigned
        self.assertEqual(loc["total_extra"], 1)  # 1 unassigned

    # ── Without solver: mix of assigned and unassigned ───────────────

    def test_withoutSolver_mixedAssignedAndUnassigned_extraIsCorrect(self, mock_kc):
        pl = PickupLocationFactory.create(name="Hofladen")
        sub = self._make_subscription()

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=self.roggenbrot,
        )
        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=None,
        )
        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=None,
        )

        result = self._run_with_locations([pl])

        loc = result["locations"][0]
        self.assertEqual(loc["total_baked"], 3)
        self.assertEqual(loc["total_ordered"], 1)
        self.assertEqual(loc["total_extra"], 2)

    # ── Without solver: multiple locations ───────────────────────────

    def test_withoutSolver_multipleLocations_eachHasOwnCounts(self, mock_kc):
        pl1 = PickupLocationFactory.create(name="Hofladen")
        pl2 = PickupLocationFactory.create(name="Marktstand")

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=self._make_subscription(),
            pickup_location=pl1,
            bread=self.roggenbrot,
        )
        for _ in range(2):
            BreadDeliveryFactory.create(
                year=self.YEAR,
                delivery_week=self.WEEK,
                subscription=self._make_subscription(),
                pickup_location=pl2,
                bread=self.dinkelkruste,
            )

        result = self._run_with_locations([pl1, pl2])

        self.assertEqual(len(result["locations"]), 2)

        loc_map = {loc["name"]: loc for loc in result["locations"]}

        self.assertEqual(loc_map["Hofladen"]["total_ordered"], 1)
        self.assertEqual(loc_map["Marktstand"]["total_ordered"], 2)
        self.assertEqual(result["grand_total_ordered"], 3)

    # ── Without solver: locations sorted alphabetically ──────────────

    def test_withoutSolver_locationsSortedAlphabetically(self, mock_kc):
        pl_z = PickupLocationFactory.create(name="Zentrallager")
        pl_a = PickupLocationFactory.create(name="Abholpunkt")

        for pickup_location in [pl_z, pl_a]:
            BreadDeliveryFactory.create(
                year=self.YEAR,
                delivery_week=self.WEEK,
                subscription=self._make_subscription(),
                pickup_location=pickup_location,
                bread=self.roggenbrot,
            )

        result = self._run_with_locations([pl_z, pl_a])

        names = [loc["name"] for loc in result["locations"]]
        self.assertEqual(names, ["Abholpunkt", "Zentrallager"])

    # ── Without solver: bread_names sorted ───────────────────────────

    def test_withoutSolver_breadNamesSortedAlphabetically(self, mock_kc):
        pl = PickupLocationFactory.create(name="Hofladen")
        sub = self._make_subscription()

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=self.roggenbrot,
        )
        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=self.dinkelkruste,
        )

        result = self._run_with_locations([pl])

        self.assertEqual(result["bread_names"], ["Dinkelkruste", "Roggenbrot"])

    # ── Without solver: bread_totals ─────────────────────────────────

    def test_withoutSolver_breadTotals_bakedIsZeroExtraIsZero(self, mock_kc):
        pl = PickupLocationFactory.create(name="Hofladen")
        sub = self._make_subscription()

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=self.roggenbrot,
        )

        result = self._run_with_locations([pl])

        self.assertEqual(result["bread_totals"]["Roggenbrot"]["baked"], 0)
        self.assertEqual(result["bread_totals"]["Roggenbrot"]["ordered"], 1)
        self.assertEqual(result["bread_totals"]["Roggenbrot"]["extra"], 0)

    # ══════════════════════════════════════════════════════════════════
    # WITH SOLVER RESULTS (BreadsPerPickupLocationPerWeek exists)
    # ══════════════════════════════════════════════════════════════════

    # ── With solver: basic baked and ordered ─────────────────────────

    def test_withSolver_bakedAndOrdered_calculatesExtraCorrectly(self, mock_kc):
        pl = PickupLocationFactory.create(name="Hofladen")
        sub = self._make_subscription()

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.roggenbrot,
            count=10,
        )

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=self.roggenbrot,
        )

        result = self._run_with_locations([pl])

        self.assertTrue(result["has_solver_results"])
        loc = result["locations"][0]
        self.assertEqual(loc["breads"]["Roggenbrot"]["baked"], 10)
        self.assertEqual(loc["breads"]["Roggenbrot"]["ordered"], 1)
        self.assertEqual(loc["breads"]["Roggenbrot"]["extra"], 9)
        self.assertEqual(loc["total_baked"], 10)
        self.assertEqual(loc["total_ordered"], 1)
        self.assertEqual(loc["total_extra"], 9)

    # ── With solver: baked only (no orders) ──────────────────────────

    def test_withSolver_bakedButNoOrders_orderedIsZero(self, mock_kc):
        pl = PickupLocationFactory.create(name="Hofladen")

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.roggenbrot,
            count=8,
        )

        result = self._run_with_locations([pl])

        self.assertTrue(result["has_solver_results"])
        loc = result["locations"][0]
        self.assertEqual(loc["breads"]["Roggenbrot"]["baked"], 8)
        self.assertEqual(loc["breads"]["Roggenbrot"]["ordered"], 0)
        self.assertEqual(loc["breads"]["Roggenbrot"]["extra"], 8)

    # ── With solver: orders only (ordered but not in solver → no baked) ──

    def test_withSolver_orderedBreadNotInSolver_bakedIsZero(self, mock_kc):
        pl = PickupLocationFactory.create(name="Hofladen")
        sub = self._make_subscription()

        # Solver result for roggenbrot, but member ordered dinkelkruste
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.roggenbrot,
            count=5,
        )

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=self.dinkelkruste,
        )

        result = self._run_with_locations([pl])

        self.assertTrue(result["has_solver_results"])
        loc = result["locations"][0]
        self.assertEqual(loc["breads"]["Dinkelkruste"]["baked"], 0)
        self.assertEqual(loc["breads"]["Dinkelkruste"]["ordered"], 1)
        self.assertEqual(loc["breads"]["Dinkelkruste"]["extra"], -1)

    # ── With solver: multiple breads and locations ───────────────────

    def test_withSolver_multipleLocationsMultipleBreads_totalsCorrect(self, mock_kc):
        pl1 = PickupLocationFactory.create(name="Hofladen")
        pl2 = PickupLocationFactory.create(name="Marktstand")

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl1,
            bread=self.roggenbrot,
            count=6,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl2,
            bread=self.dinkelkruste,
            count=4,
        )

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=self._make_subscription(),
            pickup_location=pl1,
            bread=self.roggenbrot,
        )
        for _ in range(2):
            BreadDeliveryFactory.create(
                year=self.YEAR,
                delivery_week=self.WEEK,
                subscription=self._make_subscription(),
                pickup_location=pl2,
                bread=self.dinkelkruste,
            )

        result = self._run_with_locations([pl1, pl2])

        self.assertTrue(result["has_solver_results"])
        self.assertEqual(result["grand_total_baked"], 10)
        self.assertEqual(result["grand_total_ordered"], 3)
        self.assertEqual(result["grand_total_extra"], 7)

    # ── With solver: locations sorted alphabetically ─────────────────

    def test_withSolver_locationsSortedAlphabetically(self, mock_kc):
        pl_z = PickupLocationFactory.create(name="Zentrallager")
        pl_a = PickupLocationFactory.create(name="Abholpunkt")

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl_z,
            bread=self.roggenbrot,
            count=3,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl_a,
            bread=self.roggenbrot,
            count=2,
        )

        result = self._run_with_locations([pl_z, pl_a])

        names = [loc["name"] for loc in result["locations"]]
        self.assertEqual(names, ["Abholpunkt", "Zentrallager"])

    # ── With solver: bread_names sorted ──────────────────────────────

    def test_withSolver_breadNamesSortedAlphabetically(self, mock_kc):
        pl = PickupLocationFactory.create(name="Hofladen")

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.roggenbrot,
            count=3,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.dinkelkruste,
            count=2,
        )

        result = self._run_with_locations([pl])

        self.assertEqual(result["bread_names"], ["Dinkelkruste", "Roggenbrot"])

    # ── With solver: bread_totals across locations ───────────────────

    def test_withSolver_breadTotalsAcrossLocations_sumCorrectly(self, mock_kc):
        pl1 = PickupLocationFactory.create(name="Hofladen")
        pl2 = PickupLocationFactory.create(name="Marktstand")
        sub = self._make_subscription()

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl1,
            bread=self.roggenbrot,
            count=4,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl2,
            bread=self.roggenbrot,
            count=6,
        )

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl1,
            bread=self.roggenbrot,
        )

        result = self._run_with_locations([pl1, pl2])

        self.assertEqual(result["bread_totals"]["Roggenbrot"]["baked"], 10)
        self.assertEqual(result["bread_totals"]["Roggenbrot"]["ordered"], 1)
        self.assertEqual(result["bread_totals"]["Roggenbrot"]["extra"], 9)

    # ── With solver: multiple solver entries same location same bread sum ─

    def test_withSolver_multipleSolverEntriesSameBread_sumsBaked(self, mock_kc):
        pl1 = PickupLocationFactory.create(name="Hofladen")
        pl2 = PickupLocationFactory.create(name="Marktstand")

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl1,
            bread=self.roggenbrot,
            count=3,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl2,
            bread=self.roggenbrot,
            count=7,
        )

        result = self._run_with_locations([pl1, pl2])

        self.assertEqual(result["bread_totals"]["Roggenbrot"]["baked"], 10)

    # ══════════════════════════════════════════════════════════════════
    # FILTERING — different day/week excluded
    # ══════════════════════════════════════════════════════════════════

    def test_deliveriesForDifferentLocation_excluded(self, mock_kc):
        pl_included = PickupLocationFactory.create(name="Hofladen")
        pl_excluded = PickupLocationFactory.create(name="Anderer Ort")
        sub = self._make_subscription()

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl_excluded,
            bread=self.roggenbrot,
        )

        # Only pl_included is returned as a day location
        result = self._run_with_locations([pl_included])

        self.assertEqual(result["locations"], [])
        self.assertEqual(result["grand_total_ordered"], 0)

    def test_solverResultsForDifferentLocation_excluded(self, mock_kc):
        pl_included = PickupLocationFactory.create(name="Hofladen")
        pl_excluded = PickupLocationFactory.create(name="Anderer Ort")

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl_excluded,
            bread=self.roggenbrot,
            count=10,
        )

        result = self._run_with_locations([pl_included])

        self.assertFalse(result["has_solver_results"])
        self.assertEqual(result["locations"], [])

    # ══════════════════════════════════════════════════════════════════
    # GRAND TOTALS
    # ══════════════════════════════════════════════════════════════════

    def test_withSolver_grandTotals_sumAllLocations(self, mock_kc):
        pl1 = PickupLocationFactory.create(name="Hofladen")
        pl2 = PickupLocationFactory.create(name="Marktstand")
        sub = self._make_subscription()

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl1,
            bread=self.roggenbrot,
            count=5,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl2,
            bread=self.dinkelkruste,
            count=3,
        )

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=sub,
            pickup_location=pl1,
            bread=self.roggenbrot,
        )

        result = self._run_with_locations([pl1, pl2])

        self.assertEqual(result["grand_total_baked"], 8)
        self.assertEqual(result["grand_total_ordered"], 1)
        self.assertEqual(result["grand_total_extra"], 7)

    def test_withoutSolver_grandTotals_sumAllLocations(self, mock_kc):
        pl1 = PickupLocationFactory.create(name="Hofladen")
        pl2 = PickupLocationFactory.create(name="Marktstand")

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=self._make_subscription(),
            pickup_location=pl1,
            bread=self.roggenbrot,
        )
        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=self._make_subscription(),
            pickup_location=pl2,
            bread=None,
        )

        result = self._run_with_locations([pl1, pl2])

        self.assertFalse(result["has_solver_results"])
        self.assertEqual(result["grand_total_baked"], 2)  # total deliveries
        self.assertEqual(result["grand_total_ordered"], 1)
        self.assertEqual(result["grand_total_extra"], 1)

    # ══════════════════════════════════════════════════════════════════
    # STATIONS SHARING A NAME
    # ══════════════════════════════════════════════════════════════════

    def test_withoutSolver_twoLocationsSameName_stayTwoRows(self, mock_kc):
        """
        Only the (name, coordinates) triple is unique, so two stations in
        different villages may well both be called "Hofpunkt". The
        Verteilliste is printed per station: merging them into one row would
        send both stations' loaves to whichever one is unpacked first.
        """
        pl1 = PickupLocationFactory.create(name="Hofpunkt", coords_lon=1)
        pl2 = PickupLocationFactory.create(name="Hofpunkt", coords_lon=2)

        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=self._make_subscription(),
            pickup_location=pl1,
            bread=self.roggenbrot,
        )
        for _ in range(2):
            BreadDeliveryFactory.create(
                year=self.YEAR,
                delivery_week=self.WEEK,
                subscription=self._make_subscription(),
                pickup_location=pl2,
                bread=self.roggenbrot,
            )

        result = self._run_with_locations([pl1, pl2])

        self.assertEqual([loc["name"] for loc in result["locations"]], 2 * ["Hofpunkt"])
        self.assertEqual(
            sorted(loc["total_ordered"] for loc in result["locations"]), [1, 2]
        )
        self.assertEqual(result["grand_total_ordered"], 3)

    def test_withSolver_twoLocationsSameName_stayTwoRows(self, mock_kc):
        pl1 = PickupLocationFactory.create(name="Hofpunkt", coords_lon=1)
        pl2 = PickupLocationFactory.create(name="Hofpunkt", coords_lon=2)

        for pickup_location, count in [(pl1, 4), (pl2, 7)]:
            BreadsPerPickupLocationPerWeekFactory.create(
                year=self.YEAR,
                delivery_week=self.WEEK,
                pickup_location=pickup_location,
                bread=self.roggenbrot,
                count=count,
            )

        result = self._run_with_locations([pl1, pl2])

        self.assertTrue(result["has_solver_results"])
        self.assertEqual([loc["name"] for loc in result["locations"]], 2 * ["Hofpunkt"])
        self.assertEqual(
            sorted(loc["breads"]["Roggenbrot"]["baked"] for loc in result["locations"]),
            [4, 7],
        )
        self.assertEqual(result["bread_totals"]["Roggenbrot"]["baked"], 11)
