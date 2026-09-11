from unittest.mock import patch

from tapir.bakery.models import BreadsToBakePerWeek
from tapir.bakery.services.baking_list_service import BakingListService
from tapir.bakery.tests.factories import (
    BreadsToBakePerWeekFactory,
    BreadFactory,
    BreadsPerPickupLocationPerWeekFactory,
    StoveSessionFactory,
)
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak


@patch("tapir.wirgarten.tests.factories.KeycloakUserManager.get_keycloak_client")
class TestBakingListService(TapirIntegrationTest):
    YEAR = 2026
    WEEK = 11
    DAY = 3

    def setUp(self):
        super().setUp()
        set_bypass_keycloak()
        self.roggenbrot = BreadFactory.create(name="Roggenbrot")
        self.dinkelkruste = BreadFactory.create(name="Dinkelkruste")

    # ── No data ──────────────────────────────────────────────────────

    def _plan_to_bake(self, bread, quantity, session_number=1, layer_number=1):
        """
        A baking plan as the solver writes it: the oven schedule plus the
        per-bread total the Backliste reports as "baked". Both go in one
        transaction in save_solution_to_db, so a test that sets up one without
        the other is describing a state that cannot occur.
        """
        StoveSessionFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            delivery_day=self.DAY,
            session_number=session_number,
            layer_number=layer_number,
            bread=bread,
            quantity=quantity,
        )
        row, created = BreadsToBakePerWeek.objects.get_or_create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            delivery_day=self.DAY,
            bread=bread,
            defaults={"quantity": quantity},
        )
        if not created:
            row.quantity += quantity
            row.save()

    def test_getBakingList_noData_returnsEmptyResult(self, mock_kc):
        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(result["breads"], [])
        self.assertEqual(result["total_deliveries"], 0)
        self.assertEqual(result["total_baked"], 0)
        self.assertEqual(result["total_extra"], 0)
        self.assertEqual(result["stove_sessions"], [])

    # ── Deliveries only (no baking) ─────────────────────────────────

    def test_getBakingList_deliveriesOnly_showsDeliveriesAndZeroBaked(self, mock_kc):
        pl = PickupLocationFactory.create()

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.roggenbrot,
            count=5,
        )

        with patch.object(
            BakingListService,
            "get_pickup_location_ids_for_day",
            return_value=[pl.id],
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(len(result["breads"]), 1)
        self.assertEqual(result["breads"][0]["name"], "Roggenbrot")
        self.assertEqual(result["breads"][0]["deliveries"], 5)
        self.assertEqual(result["breads"][0]["baked"], 0)
        self.assertEqual(result["breads"][0]["extra"], -5)
        self.assertEqual(result["total_deliveries"], 5)
        self.assertEqual(result["total_baked"], 0)
        self.assertEqual(result["total_extra"], -5)

    # ── Baking only (no deliveries) ─────────────────────────────────

    def test_getBakingList_bakingOnly_showsBakedAndZeroDeliveries(self, mock_kc):
        self._plan_to_bake(self.roggenbrot, 8, session_number=1, layer_number=1)

        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(len(result["breads"]), 1)
        self.assertEqual(result["breads"][0]["name"], "Roggenbrot")
        self.assertEqual(result["breads"][0]["deliveries"], 0)
        self.assertEqual(result["breads"][0]["baked"], 8)
        self.assertEqual(result["breads"][0]["extra"], 8)
        self.assertEqual(result["total_baked"], 8)
        self.assertEqual(result["total_extra"], 8)

    # ── Deliveries + baking combined ────────────────────────────────

    def test_getBakingList_deliveriesAndBaking_calculatesExtraCorrectly(self, mock_kc):
        pl = PickupLocationFactory.create()

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.roggenbrot,
            count=10,
        )

        self._plan_to_bake(self.roggenbrot, 12, session_number=1, layer_number=1)

        with patch.object(
            BakingListService,
            "get_pickup_location_ids_for_day",
            return_value=[pl.id],
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        bread = result["breads"][0]
        self.assertEqual(bread["name"], "Roggenbrot")
        self.assertEqual(bread["deliveries"], 10)
        self.assertEqual(bread["baked"], 12)
        self.assertEqual(bread["extra"], 2)
        self.assertEqual(result["total_deliveries"], 10)
        self.assertEqual(result["total_baked"], 12)
        self.assertEqual(result["total_extra"], 2)

    # ── Multiple breads ─────────────────────────────────────────────

    def test_getBakingList_multipleBreads_allAreListed(self, mock_kc):
        pl = PickupLocationFactory.create()

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.roggenbrot,
            count=5,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.dinkelkruste,
            count=3,
        )

        self._plan_to_bake(self.roggenbrot, 6, session_number=1, layer_number=1)
        self._plan_to_bake(self.dinkelkruste, 4, session_number=1, layer_number=2)

        with patch.object(
            BakingListService,
            "get_pickup_location_ids_for_day",
            return_value=[pl.id],
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(len(result["breads"]), 2)
        self.assertEqual(result["total_deliveries"], 8)
        self.assertEqual(result["total_baked"], 10)
        self.assertEqual(result["total_extra"], 2)

    def test_getBakingList_multipleBreads_sortedAlphabetically(self, mock_kc):
        pl = PickupLocationFactory.create()

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.roggenbrot,
            count=1,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.dinkelkruste,
            count=1,
        )

        with patch.object(
            BakingListService,
            "get_pickup_location_ids_for_day",
            return_value=[pl.id],
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        names = [b["name"] for b in result["breads"]]
        self.assertEqual(names, ["Dinkelkruste", "Roggenbrot"])

    # ── Multiple pickup locations for same day ──────────────────────

    def test_getBakingList_multiplePickupLocationsForSameDay_sumsDeliveries(
        self, mock_kc
    ):
        pl1 = PickupLocationFactory.create()
        pl2 = PickupLocationFactory.create()

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

        with patch.object(
            BakingListService,
            "get_pickup_location_ids_for_day",
            return_value=[pl1.id, pl2.id],
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(result["breads"][0]["deliveries"], 10)
        self.assertEqual(result["total_deliveries"], 10)

    # ── Pickup location on different day is excluded ────────────────

    def test_getBakingList_pickupLocationOnDifferentDay_excluded(self, mock_kc):
        pl = PickupLocationFactory.create()

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=pl,
            bread=self.roggenbrot,
            count=10,
        )

        # Return empty list — this pickup location is NOT for self.DAY
        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(result["breads"], [])
        self.assertEqual(result["total_deliveries"], 0)

    # ── Stove sessions on different day excluded ────────────────────

    def test_getBakingList_stoveSessionOnDifferentDay_excluded(self, mock_kc):
        other_day = self.DAY + 1 if self.DAY < 6 else 0

        StoveSessionFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            delivery_day=other_day,
            session_number=1,
            layer_number=1,
            bread=self.roggenbrot,
            quantity=10,
        )

        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(result["stove_sessions"], [])
        self.assertEqual(result["total_baked"], 0)

    # ── Stove sessions on different week excluded ───────────────────

    def test_getBakingList_stoveSessionOnDifferentWeek_excluded(self, mock_kc):
        StoveSessionFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK + 1,
            delivery_day=self.DAY,
            session_number=1,
            layer_number=1,
            bread=self.roggenbrot,
            quantity=10,
        )

        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(result["stove_sessions"], [])
        self.assertEqual(result["total_baked"], 0)

    # ── Stove session structure ─────────────────────────────────────

    def test_getBakingList_singleStoveSession_returnsCorrectStructure(self, mock_kc):
        self._plan_to_bake(self.roggenbrot, 6, session_number=1, layer_number=1)
        self._plan_to_bake(self.dinkelkruste, 4, session_number=1, layer_number=2)

        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(len(result["stove_sessions"]), 1)
        session = result["stove_sessions"][0]
        self.assertEqual(session["session"], 1)
        self.assertEqual(len(session["layers"]), 2)
        self.assertEqual(session["layers"][0]["layer"], 1)
        self.assertEqual(session["layers"][0]["bread_name"], "Roggenbrot")
        self.assertEqual(session["layers"][0]["quantity"], 6)
        self.assertEqual(session["layers"][1]["layer"], 2)
        self.assertEqual(session["layers"][1]["bread_name"], "Dinkelkruste")
        self.assertEqual(session["layers"][1]["quantity"], 4)

    def test_getBakingList_multipleStoveSessions_sortedBySessionNumber(self, mock_kc):
        self._plan_to_bake(self.dinkelkruste, 5, session_number=2, layer_number=1)
        self._plan_to_bake(self.roggenbrot, 6, session_number=1, layer_number=1)

        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(len(result["stove_sessions"]), 2)
        self.assertEqual(result["stove_sessions"][0]["session"], 1)
        self.assertEqual(result["stove_sessions"][1]["session"], 2)

    def test_getBakingList_stoveSessionLayers_sortedByLayerNumber(self, mock_kc):
        self._plan_to_bake(self.roggenbrot, 2, session_number=1, layer_number=3)
        self._plan_to_bake(self.dinkelkruste, 4, session_number=1, layer_number=1)

        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        layers = result["stove_sessions"][0]["layers"]
        self.assertEqual(layers[0]["layer"], 1)
        self.assertEqual(layers[1]["layer"], 3)

    # ── Multiple stove sessions sum baked totals ────────────────────

    def test_getBakingList_multipleSessions_bakeTotalsSumCorrectly(self, mock_kc):
        self._plan_to_bake(self.roggenbrot, 6, session_number=1, layer_number=1)
        self._plan_to_bake(self.roggenbrot, 4, session_number=2, layer_number=1)

        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(result["breads"][0]["baked"], 10)
        self.assertEqual(result["total_baked"], 10)

    # ── Whole-week and per-day plans in the same week ───────────────

    def test_getBakingList_wholeWeekPlanOnly_isUsedForTheDay(self, mock_kc):
        # A whole-week run writes delivery_day=None, and the Backliste is still
        # rendered per day.
        BreadsToBakePerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            delivery_day=None,
            bread=self.roggenbrot,
            quantity=10,
        )
        StoveSessionFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            delivery_day=None,
            session_number=1,
            layer_number=1,
            bread=self.roggenbrot,
            quantity=10,
        )

        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(result["total_baked"], 10)
        self.assertEqual(len(result["stove_sessions"]), 1)

    def test_getBakingList_dayPlanSupersedesWholeWeekPlan_notAddedToIt(self, mock_kc):
        # Planning a day after the week leaves both shapes in the table.
        # Summing them would report the same loaves twice.
        BreadsToBakePerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            delivery_day=None,
            bread=self.roggenbrot,
            quantity=10,
        )
        StoveSessionFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            delivery_day=None,
            session_number=1,
            layer_number=1,
            bread=self.roggenbrot,
            quantity=10,
        )
        self._plan_to_bake(self.roggenbrot, 4)

        with patch.object(
            BakingListService, "get_pickup_location_ids_for_day", return_value=[]
        ):
            result = BakingListService.get_baking_list(
                year=self.YEAR, week=self.WEEK, day=self.DAY
            )

        self.assertEqual(result["breads"][0]["baked"], 4)
        self.assertEqual(result["total_baked"], 4)
        self.assertEqual(len(result["stove_sessions"][0]["layers"]), 1)
