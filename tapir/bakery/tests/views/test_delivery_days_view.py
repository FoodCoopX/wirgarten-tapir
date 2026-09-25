from django.urls import reverse
from rest_framework import status

from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDeliveryDaysView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create())

    def test_get_locationOpenOnSeveralDays_returnsOnlyTheEarliestDay(self):
        create_pickup_location_with_opening_times([1, 4])
        create_pickup_location_with_opening_times([3])

        response = self.client.get(reverse("bakery:delivery-days"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["days"], [1, 3])

    def test_get_noOpeningTimes_returnsEmptyList(self):
        PickupLocationFactory.create()

        response = self.client.get(reverse("bakery:delivery-days"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["days"], [])

    def test_get_unauthenticated_returns401(self):
        self.client.logout()

        response = self.client.get(reverse("bakery:delivery-days"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
