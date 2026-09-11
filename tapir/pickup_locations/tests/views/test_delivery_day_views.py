import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


def open_on(pickup_location, *days):
    for day in days:
        PickupLocationOpeningTime.objects.create(
            pickup_location=pickup_location,
            day_of_week=day,
            open_time=datetime.time(8),
            close_time=datetime.time(18),
        )


class TestDeliveryDayViews(TapirIntegrationTest):
    """
    Both views answer the question the pickup lists, the baking list and the
    solver also ask - "which station is delivered on which weekday" - through
    PickupLocationDeliveryDayService.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create())

    def test_deliveryDays_returnsOnlyTheEarliestDayPerLocation(self):
        # A station open Tuesday and Friday is delivered on Tuesday; Friday
        # must not show up as a delivery day on its account.
        open_on(PickupLocationFactory.create(name="Hofladen"), 1, 4)
        open_on(PickupLocationFactory.create(name="Marktstand", coords_lon=1), 3)

        response = self.client.get(reverse("pickup_locations:delivery_days"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["days"], [1, 3])

    def test_deliveryDays_noOpeningTimes_returnsEmptyList(self):
        PickupLocationFactory.create(name="Hofladen")

        response = self.client.get(reverse("pickup_locations:delivery_days"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["days"], [])

    def test_deliveryDays_unauthenticated_isRejected(self):
        self.client.logout()

        response = self.client.get(reverse("pickup_locations:delivery_days"))

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_byDeliveryDay_returnsOnlyStationsDeliveredThatDay(self):
        open_on(PickupLocationFactory.create(name="Hofladen"), 1, 4)
        open_on(PickupLocationFactory.create(name="Marktstand", coords_lon=1), 4)

        response = self.client.get(
            reverse("pickup_locations:pickup_locations_by_delivery_day"),
            {"day_of_week": 4},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [entry["name"] for entry in response.data["pickup_locations"]],
            ["Marktstand"],
        )

    def test_byDeliveryDay_noStationsThatDay_returnsEmptyListNot404(self):
        # The 404 with a diagnostic payload reached the only caller as a thrown
        # ResponseError, so the allocation modal broke instead of showing a
        # day with no stations.
        open_on(PickupLocationFactory.create(name="Hofladen"), 1)

        response = self.client.get(
            reverse("pickup_locations:pickup_locations_by_delivery_day"),
            {"day_of_week": 4},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pickup_locations"], [])

    def test_byDeliveryDay_monday_isNotTreatedAsMissingParameter(self):
        # Days are 0-based (0 = Montag), so the guard on a missing parameter
        # must not treat the string "0" as absent.
        open_on(PickupLocationFactory.create(name="Hofpunkt"), 0)

        response = self.client.get(
            reverse("pickup_locations:pickup_locations_by_delivery_day"),
            {"day_of_week": 0},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [entry["name"] for entry in response.data["pickup_locations"]],
            ["Hofpunkt"],
        )

    def test_byDeliveryDay_missingParameter_returns400(self):
        response = self.client.get(
            reverse("pickup_locations:pickup_locations_by_delivery_day")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_byDeliveryDay_nonNumericParameter_returns400(self):
        response = self.client.get(
            reverse("pickup_locations:pickup_locations_by_delivery_day"),
            {"day_of_week": "Freitag"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_byDeliveryDay_unauthenticated_isRejected(self):
        self.client.logout()

        response = self.client.get(
            reverse("pickup_locations:pickup_locations_by_delivery_day"),
            {"day_of_week": 1},
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
