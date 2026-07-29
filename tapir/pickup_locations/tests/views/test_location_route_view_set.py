from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    LocationRouteFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestLocationRouteViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_list_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(reverse("pickup_locations:location_routes-list"))

        self.assertStatusCode(response, expected_status_code=status.HTTP_403_FORBIDDEN)

    def test_get_default_returnsCorrectData(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        location_route = LocationRouteFactory.create(name="lr_name_1")
        LocationRouteFactory.create(name="lr_name_2")

        PickupLocationFactory.create(name="pl_name_1", location_route=location_route)
        PickupLocationFactory.create(name="pl_name_2", location_route=location_route)

        response = self.client.get(reverse("pickup_locations:location_routes-list"))

        self.assertStatusCode(response, expected_status_code=status.HTTP_200_OK)

        response_content = response.json()
        self.assertEqual(2, len(response_content))

        route_1 = response_content[0]
        self.assertEqual("lr_name_1", route_1["name"])
        self.assertEqual(["pl_name_1", "pl_name_2"], route_1["pickup_location_names"])

        route_2 = response_content[1]
        self.assertEqual("lr_name_2", route_2["name"])
        self.assertEqual(0, len(route_2["pickup_location_names"]))
