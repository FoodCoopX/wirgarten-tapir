from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    PreferredBread,
)
from tapir.bakery.tests.factories import (
    BreadSubscriptionFactory,
    AvailableBreadsForDeliveryDayFactory,
    BreadCapacityPickupLocationFactory,
    BreadDeliveryFactory,
    BreadFactory,
    BreadsPerPickupLocationPerWeekFactory,
    enable_bakery,
)
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

YEAR = 2026
WEEK = 11
DAY = 3


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


class TestAvailableBreadsForDeliveryListViewGet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:breads-for-delivery-list")

    def test_get_noBreads_returnsEmptyList(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["breads"], [])
        self.assertEqual(response.data["year"], YEAR)
        self.assertEqual(response.data["delivery_week"], WEEK)
        self.assertEqual(response.data["delivery_day"], DAY)

    def test_get_withBreads_returnsSortedByName(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread_z = BreadFactory.create(name="Zopf", is_active=True)
        bread_a = BreadFactory.create(name="Anisbrot", is_active=True)

        AvailableBreadsForDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread_z
        )
        AvailableBreadsForDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread_a
        )

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [b["name"] for b in response.data["breads"]]
        self.assertEqual(names, ["Anisbrot", "Zopf"])

    def test_get_inactiveBreadExcluded(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread_active = BreadFactory.create(name="Roggenbrot", is_active=True)
        bread_inactive = BreadFactory.create(name="Altbrot", is_active=False)

        AvailableBreadsForDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread_active
        )
        AvailableBreadsForDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread_inactive
        )

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["breads"]), 1)
        self.assertEqual(response.data["breads"][0]["name"], "Roggenbrot")

    def test_get_differentWeekExcluded(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread = BreadFactory.create(name="Roggenbrot", is_active=True)
        AvailableBreadsForDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK + 1, delivery_day=DAY, bread=bread
        )

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["breads"], [])

    def test_get_missingParams_returnsBadRequest(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(self.url, {"year": YEAR})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_unauthenticated_returns401or403(self):
        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


class TestAvailableBreadsForDeliveryListViewPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:breads-for-delivery-list")

    def test_post_activateBread_createsEntry(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread = BreadFactory.create(name="Roggenbrot")

        response = self.client.post(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "bread_id": str(bread.id),
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["created"])
        self.assertTrue(
            AvailableBreadsForDeliveryDay.objects.filter(
                year=YEAR,
                delivery_week=WEEK,
                delivery_day=DAY,
                bread=bread,
            ).exists()
        )

    def test_post_activateBreadTwice_notCreatedAgain(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread = BreadFactory.create(name="Roggenbrot")
        AvailableBreadsForDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread
        )

        response = self.client.post(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "bread_id": str(bread.id),
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertFalse(response.data["created"])

    def test_post_deactivateBread_deletesEntry(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread = BreadFactory.create(name="Roggenbrot")
        AvailableBreadsForDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread
        )

        response = self.client.post(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "bread_id": str(bread.id),
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["deleted"])
        self.assertFalse(
            AvailableBreadsForDeliveryDay.objects.filter(
                year=YEAR,
                delivery_week=WEEK,
                delivery_day=DAY,
                bread=bread,
            ).exists()
        )

    def test_post_deactivateNonexistent_deletedFalse(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread = BreadFactory.create(name="Roggenbrot")

        response = self.client.post(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "bread_id": str(bread.id),
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["deleted"])

    def test_post_nonexistentBread_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.post(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "bread_id": "00000000-0000-0000-0000-000000000000",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestPickupListView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:pickup-list")

    def test_get_noDeliveries_returnsEmptyEntries(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl = PickupLocationFactory.create()

        response = self.client.get(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "pickup_location_id": str(pl.id),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["lists"][0]["entries"], [])

    def test_get_withDeliveries_returnsEntries(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl = PickupLocationFactory.create()
        bread = BreadFactory.create(name="Roggenbrot")
        member = MemberFactory.create()
        sub = BreadSubscriptionFactory.create(member=member)

        BreadCapacityPickupLocationFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pl,
            bread=bread,
            capacity=10,
        )

        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=bread,
        )

        response = self.client.get(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "pickup_location_id": str(pl.id),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pickup_list = response.data["lists"][0]
        self.assertEqual(pickup_list["pickup_location_id"], str(pl.id))
        self.assertEqual(len(pickup_list["entries"]), 1)
        self.assertIn("Roggenbrot", pickup_list["bread_names"])

    def test_get_severalStationsInOneRequest_returnsOneListEach(self):
        # The point of the batched form: one request, one shared cache, so the
        # week is grouped once instead of once per station.
        self.client.force_login(MemberFactory.create(is_superuser=True))
        first = PickupLocationFactory.create()
        second = PickupLocationFactory.create()

        response = self.client.get(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "pickup_location_ids[]": [str(first.id), str(second.id)],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [entry["pickup_location_id"] for entry in response.data["lists"]],
            [str(first.id), str(second.id)],
        )

    def test_get_withoutAnyStation_returns400(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(
            self.url, {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_unauthenticated_returns401or403(self):
        response = self.client.get(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "pickup_location_id": "some-id",
            },
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


class TestSolverPreviewView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:solver-preview")

    @patch("tapir.bakery.solver.solve_bread_planning_all")
    @patch("tapir.bakery.solver.collect_solver_input")
    def test_post_noData_returns422(self, mock_collect, mock_solve):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        mock_collect.return_value = None

        response = self.client.post(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    @patch("tapir.bakery.solver.solve_bread_planning_all")
    @patch("tapir.bakery.solver.collect_solver_input")
    def test_post_noSolution_returns422(self, mock_collect, mock_solve):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        mock_collect.return_value = {
            "breads": [],
            "locations": [],
            "deliveries": [],
        }
        mock_solve.return_value = {"solutions": [], "diagnostics": []}

        response = self.client.post(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    @patch("tapir.bakery.solver.solve_bread_planning_all")
    @patch("tapir.bakery.solver.collect_solver_input")
    def test_post_withSolutions_returnsSummaries(self, mock_collect, mock_solve):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread = BreadFactory.create(name="Roggenbrot")

        mock_collect.return_value = {
            "breads": [bread],
            "locations": [],
            "deliveries": [],
        }
        mock_solve.return_value = {
            "solutions": [
                {
                    "bread_quantities": {bread.id: 10},
                    "remaining_quantities": {bread.id: 2},
                    "stove_sessions": [[(bread.id, 10)]],
                    "distribution": {},
                }
            ],
            "diagnostics": [],
        }

        response = self.client.post(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_solutions"], 1)
        self.assertEqual(len(response.data["solutions"]), 1)

        solution = response.data["solutions"][0]
        self.assertEqual(solution["index"], 0)
        self.assertEqual(solution["total_baked"], 10)
        self.assertEqual(solution["total_remaining"], 2)

    def test_post_unauthenticated_returns401or403(self):
        response = self.client.post(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
            format="json",
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


class TestSolverPreviewDetailView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:solver-preview-detail")

    def test_get_noCache_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        cache.delete(f"solver_solutions_{YEAR}_{WEEK}_{DAY}")

        response = self.client.get(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "solution_index": 0,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_withCache_returnsDetail(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread = BreadFactory.create(name="Roggenbrot")
        pl = PickupLocationFactory.create(name="Hofladen")

        cache_key = f"solver_solutions_{YEAR}_{WEEK}_{DAY}"
        cache.set(
            cache_key,
            [
                {
                    "bread_quantities": {bread.id: 10},
                    "remaining_quantities": {bread.id: 2},
                    "stove_sessions": [[(bread.id, 10)]],
                    "distribution": {(bread.id, pl.id): 8},
                }
            ],
            timeout=3600,
        )

        response = self.client.get(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "solution_index": 0,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["solution_index"], 0)
        self.assertEqual(response.data["total_solutions"], 1)
        self.assertTrue(len(response.data["quantities"]) > 0)
        self.assertTrue(len(response.data["stove_sessions"]) > 0)
        self.assertTrue(len(response.data["distribution"]) > 0)

    def test_get_indexOutOfRange_clampedToLast(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread = BreadFactory.create(name="Roggenbrot")

        cache_key = f"solver_solutions_{YEAR}_{WEEK}_{DAY}"
        cache.set(
            cache_key,
            [
                {
                    "bread_quantities": {bread.id: 5},
                    "remaining_quantities": {bread.id: 1},
                    "stove_sessions": [],
                    "distribution": {},
                }
            ],
            timeout=3600,
        )

        response = self.client.get(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "solution_index": 99,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["solution_index"], 0)


class TestSolverApplyView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:solver-apply")

    def test_post_noCache_returns404(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        cache.delete(f"solver_solutions_{YEAR}_{WEEK}_{DAY}")

        response = self.client.post(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "solution_index": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("tapir.bakery.solver.save_solution_to_db")
    def test_post_withCache_appliesSolution(self, mock_save):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        bread = BreadFactory.create(name="Roggenbrot")

        cached_results = [
            {
                "bread_quantities": {bread.id: 10},
                "remaining_quantities": {bread.id: 2},
                "stove_sessions": [],
                "distribution": {},
            }
        ]
        cache_key = f"solver_solutions_{YEAR}_{WEEK}_{DAY}"
        cache.set(cache_key, cached_results, timeout=3600)

        response = self.client.post(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "solution_index": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["solution_index"], 0)
        mock_save.assert_called_once_with(YEAR, WEEK, DAY, cached_results[0])

    def test_post_unauthenticated_returns401or403(self):
        response = self.client.post(
            self.url,
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "solution_index": 0,
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


class TestPreferenceSatisfactionMetricsView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:metrics-preference-satisfaction")

    def test_get_noDeliveries_returnsEmptyLocations(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["locations"], [])

    def test_get_withDeliveriesAndSolverResults_returnsMetrics(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl = create_pickup_location_with_delivery_day(DAY, name="Hofladen")
        bread = BreadFactory.create(name="Roggenbrot")
        member = MemberFactory.create()
        sub = BreadSubscriptionFactory.create(member=member)

        BreadCapacityPickupLocationFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pl,
            bread=bread,
            capacity=10,
        )

        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=bread,
        )

        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pl,
            bread=bread,
            count=5,
        )

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["locations"]), 1)

        loc = response.data["locations"][0]
        self.assertEqual(loc["pickup_location_name"], "Hofladen")
        self.assertEqual(loc["total_deliveries"], 1)
        self.assertEqual(loc["directly_chosen"], 1)

    def test_get_memberWithNoFavorites_countedAsSatisfied(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl = create_pickup_location_with_delivery_day(DAY, name="Hofladen")
        bread = BreadFactory.create(name="Roggenbrot")
        member = MemberFactory.create()
        sub = BreadSubscriptionFactory.create(member=member)

        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=None,
        )

        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pl,
            bread=bread,
            count=5,
        )

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loc = response.data["locations"][0]
        self.assertEqual(loc["no_favorites"], 1)
        self.assertEqual(loc["satisfied"], 1)

    def test_get_memberWithFavoriteAvailable_gotFavorite(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl = create_pickup_location_with_delivery_day(DAY, name="Hofladen")
        bread = BreadFactory.create(name="Roggenbrot")
        member = MemberFactory.create()
        sub = BreadSubscriptionFactory.create(member=member)

        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=None,
        )

        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pl,
            bread=bread,
            count=5,
        )

        pref = PreferredBread.objects.create(member=member)
        pref.breads.add(bread)

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loc = response.data["locations"][0]
        self.assertEqual(loc["got_favorite"], 1)
        self.assertEqual(loc["satisfied"], 1)

    def test_get_memberWithFavoriteNotAvailable_noMatch(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl = create_pickup_location_with_delivery_day(DAY, name="Hofladen")
        bread_available = BreadFactory.create(name="Roggenbrot")
        bread_wanted = BreadFactory.create(name="Dinkelkruste")
        member = MemberFactory.create()
        sub = BreadSubscriptionFactory.create(member=member)

        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=None,
        )

        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pl,
            bread=bread_available,
            count=0,
        )

        pref = PreferredBread.objects.create(member=member)
        pref.breads.add(bread_wanted)

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loc = response.data["locations"][0]
        self.assertEqual(loc["no_match"], 1)

    def test_get_locationsSortedAlphabetically(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl_z = create_pickup_location_with_delivery_day(DAY, name="Zentrallager")
        pl_a = create_pickup_location_with_delivery_day(DAY, name="Abholpunkt")
        bread = BreadFactory.create(name="Roggenbrot")

        for pickup_location in [pl_z, pl_a]:
            BreadCapacityPickupLocationFactory.create(
                year=YEAR,
                delivery_week=WEEK,
                pickup_location=pickup_location,
                bread=bread,
                capacity=10,
            )
            # A member belongs to one station per week, so the second station
            # needs its own member.
            BreadDeliveryFactory.create(
                year=YEAR,
                delivery_week=WEEK,
                subscription=BreadSubscriptionFactory.create(
                    member=MemberFactory.create()
                ),
                pickup_location=pickup_location,
                bread=bread,
            )

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [loc["pickup_location_name"] for loc in response.data["locations"]]
        self.assertEqual(names, ["Abholpunkt", "Zentrallager"])

    def test_get_unauthenticated_returns401or403(self):
        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK},
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


class TestPreferredBreadStatisticsView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:preferred-bread-statistics")

    def test_get_noDeliveries_returnsZeros(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_members"], 0)
        self.assertEqual(response.data["breads"], [])

    def test_get_membersWithPreferences_returnsCounts(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl = create_pickup_location_with_delivery_day(DAY)
        bread_a = BreadFactory.create(name="Anisbrot")
        bread_r = BreadFactory.create(name="Roggenbrot")

        member1 = MemberFactory.create()
        member2 = MemberFactory.create()
        sub1 = BreadSubscriptionFactory.create(member=member1)
        sub2 = BreadSubscriptionFactory.create(member=member2)

        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub1,
            pickup_location=pl,
            bread=None,
        )
        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub2,
            pickup_location=pl,
            bread=None,
        )

        pref1 = PreferredBread.objects.create(member=member1)
        pref1.breads.add(bread_a, bread_r)

        pref2 = PreferredBread.objects.create(member=member2)
        pref2.breads.add(bread_r)

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_members"], 2)
        self.assertEqual(response.data["members_with_preferences"], 2)
        self.assertEqual(response.data["members_without_preferences"], 0)

        bread_map = {b["bread_name"]: b["count"] for b in response.data["breads"]}
        self.assertEqual(bread_map["Roggenbrot"], 2)
        self.assertEqual(bread_map["Anisbrot"], 1)

    def test_get_memberWithoutPreferences_countedAsWithout(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl = create_pickup_location_with_delivery_day(DAY)
        member = MemberFactory.create()
        sub = BreadSubscriptionFactory.create(member=member)

        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=None,
        )

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_members"], 1)
        self.assertEqual(response.data["members_without_preferences"], 1)

    def test_get_sortedByCountDescending(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        pl = create_pickup_location_with_delivery_day(DAY)
        bread_a = BreadFactory.create(name="Anisbrot")
        bread_r = BreadFactory.create(name="Roggenbrot")

        for _ in range(3):
            m = MemberFactory.create()
            s = BreadSubscriptionFactory.create(member=m)
            BreadDeliveryFactory.create(
                year=YEAR,
                delivery_week=WEEK,
                subscription=s,
                pickup_location=pl,
                bread=None,
            )
            pref = PreferredBread.objects.create(member=m)
            pref.breads.add(bread_r)

        m = MemberFactory.create()
        s = BreadSubscriptionFactory.create(member=m)
        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=s,
            pickup_location=pl,
            bread=None,
        )
        pref = PreferredBread.objects.create(member=m)
        pref.breads.add(bread_a)

        response = self.client.get(
            self.url,
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [b["bread_name"] for b in response.data["breads"]]
        self.assertEqual(names, ["Roggenbrot", "Anisbrot"])

    def test_get_plainMember_isRejected(self):
        # Its only consumer is the admin dashboard; a member has no reason to
        # read co-op wide preference statistics.
        self.client.force_login(MemberFactory.create())

        response = self.client.get(self.url, {"year": YEAR, "delivery_week": WEEK})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestBakeryEndpointsRequireCoopManage(TapirIntegrationTest):
    """
    The bakery reports expose every member's name, station and preferences, so
    a plain member must not reach them. These are the gates that make the
    bread-delivery ownership scoping meaningful rather than bypassable by URL.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create())

    def test_pickupList_plainMember_isForbidden(self):
        response = self.client.get(
            reverse("bakery:pickup-list"),
            {"year": YEAR, "week": WEEK, "pickup_location_id": "whatever"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_preferenceSatisfactionMetrics_plainMember_isForbidden(self):
        response = self.client.get(
            reverse("bakery:metrics-preference-satisfaction"),
            {"year": YEAR, "delivery_week": WEEK},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reportsPage_plainMember_isForbidden(self):
        response = self.client.get(reverse("bakery:reports"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_weeklyPlanPage_plainMember_isForbidden(self):
        response = self.client.get(reverse("bakery:weekly-plan-breads"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ingredientsLabelsPage_plainMember_isForbidden(self):
        response = self.client.get(reverse("bakery:ingredients-labels-breads"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_chooseBreadsPage_ownMemberId_isAllowed(self):
        enable_bakery()

        response = self.client.get(reverse("bakery:choose-breads"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_chooseBreadsPage_foreignMemberId_isForbidden(self):
        enable_bakery()
        victim = MemberFactory.create()

        response = self.client.get(
            reverse("bakery:choose-breads"), {"member_id": str(victim.id)}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_adminPages_bakeryDisabled_areNotFound(self):
        # The flag means the same thing on every bakery entry point: with the
        # feature off the pages do not exist, rather than rendering an empty
        # React shell over a switched-off feature.
        self.client.force_login(MemberFactory.create(is_superuser=True))

        for name in ("reports", "weekly-plan-breads", "ingredients-labels-breads"):
            with self.subTest(page=name):
                response = self.client.get(reverse(f"bakery:{name}"))
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_adminPages_bakeryDisabled_plainMemberStillGets403(self):
        # The flag check lives in get(), after the permission check, so an
        # unauthorised caller never learns whether the feature is enabled.
        for name in ("reports", "weekly-plan-breads", "ingredients-labels-breads"):
            with self.subTest(page=name):
                response = self.client.get(reverse(f"bakery:{name}"))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_chooseBreadsPage_anonymous_isRedirectedToLogin(self):
        # raise_exception=True turned the login redirect into a bare 403 on the
        # one member-facing bakery page, which is linked from member_detail.
        enable_bakery()
        self.client.logout()

        response = self.client.get(reverse("bakery:choose-breads"))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_chooseBreadsPage_bakeryDisabled_isNotFound(self):
        # The URLs are included unconditionally, so the view itself has to
        # gate on the feature flag.
        response = self.client.get(reverse("bakery:choose-breads"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_adminPages_coopManager_isAllowed(self):
        enable_bakery()
        self.client.force_login(MemberFactory.create(is_superuser=True))
        for name in ("reports", "weekly-plan-breads", "ingredients-labels-breads"):
            with self.subTest(page=name):
                response = self.client.get(reverse(f"bakery:{name}"))
                self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestSolverUnavailable(TapirIntegrationTest):
    """
    ortools is the "bakery" extra in pyproject.toml - it and its subtree are
    about 210 MB and nothing outside tapir.bakery.solver imports them. An
    installation built without the extra must get an answer it can act on from
    the two solver endpoints, not an ImportError traceback.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    @patch("tapir.bakery.views.is_solver_available", return_value=False)
    def test_solverPreview_withoutOrtools_returns503(self, _mock):
        response = self.client.post(
            reverse("bakery:solver-preview"),
            {"year": YEAR, "delivery_week": WEEK},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("ortools", response.data["error"])

    @patch("tapir.bakery.views.is_solver_available", return_value=False)
    def test_solverApply_withoutOrtools_returns503(self, _mock):
        response = self.client.post(
            reverse("bakery:solver-apply"),
            {"year": YEAR, "delivery_week": WEEK},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("ortools", response.data["error"])

    def test_isSolverAvailable_missingPackage_isFalse(self):
        from tapir.bakery import solver_availability

        with patch.object(solver_availability, "find_spec", return_value=None):
            self.assertFalse(solver_availability.is_solver_available())

    def test_isSolverAvailable_finderRaises_isFalse(self):
        # A partially removed distribution can leave a finder that throws;
        # "unavailable" is the right answer there too.
        from tapir.bakery import solver_availability

        with patch.object(
            solver_availability, "find_spec", side_effect=ImportError("gone")
        ):
            self.assertFalse(solver_availability.is_solver_available())

    def test_isSolverAvailable_inThisEnvironment_isTrue(self):
        # The dev image installs --extras bakery, so this pins that the check
        # is not simply always False.
        from tapir.bakery.solver_availability import is_solver_available

        self.assertTrue(is_solver_available())
