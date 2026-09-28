from django.urls import reverse
from rest_framework import status

from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationsByDeliveryDayView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create())

    def get(self, params):
        return self.client.get(
            reverse("bakery:pickup-locations-by-delivery-day"), params
        )

    def test_get_default_returnsOnlyLocationsDeliveredThatDay(self):
        create_pickup_location_with_opening_times([1, 4], name="Hofladen")
        create_pickup_location_with_opening_times([4], name="Marktstand")

        response = self.get({"day_of_week": 4})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [entry["name"] for entry in response.data["pickup_locations"]],
            ["Marktstand"],
        )

    def test_get_noLocationsThatDay_returnsEmptyList(self):
        create_pickup_location_with_opening_times([1])

        response = self.get({"day_of_week": 4})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pickup_locations"], [])

    def test_get_monday_returnsLocationsDeliveredOnMonday(self):
        create_pickup_location_with_opening_times([0], name="Hofpunkt")

        response = self.get({"day_of_week": 0})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [entry["name"] for entry in response.data["pickup_locations"]],
            ["Hofpunkt"],
        )

    def test_get_missingParameter_returns400(self):
        response = self.get({})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_nonNumericParameter_returns400(self):
        response = self.get({"day_of_week": "Freitag"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_unauthenticated_returns401(self):
        self.client.logout()

        response = self.get({"day_of_week": 1})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
