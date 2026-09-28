import datetime
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.pickup_location_1 = PickupLocationFactory.create(name="pickup_location_name_1")
        self.pickup_location_2 = PickupLocationFactory.create(name="pickup_location_name_2")
        self.pickup_location_3 = PickupLocationFactory.create(name="pickup_location_name_3")
        self._login_as_admin()
        self.reference_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=datetime.date.today(),
            apply_buffer_time=False,
            cache={},
        )

    def _list_pickup_location_names(self, url_name):
        url = reverse(url_name)
        response = self.client.get(url)
        self.assertStatusCode(response, status.HTTP_200_OK)
        return sorted(loc["name"] for loc in response.json())

    def test_adminList_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        response = self.client.get(reverse("pickup_locations:pickup_locations-list"))
        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_adminList_returnsAllPickupLocationsRegardlessOfDates(self):
        self.pickup_location_1.end_date = self.reference_date - datetime.timedelta(days=1)
        self.pickup_location_2.start_date = self.reference_date + datetime.timedelta(days=1)
        self.pickup_location_1.save()
        self.pickup_location_2.save()
        names = self._list_pickup_location_names("pickup_locations:pickup_locations-list")
        self.assertEqual(["pickup_location_name_1", "pickup_location_name_2", "pickup_location_name_3"], names)

    def test_publicList_noDates_returnsAllPickupLocations(self):
        names = self._list_pickup_location_names("pickup_locations:public_pickup_locations-list")
        self.assertEqual(["pickup_location_name_1", "pickup_location_name_2", "pickup_location_name_3"], names)

    def test_publicList_plWithPastEndDate_isExcluded(self):
        self.pickup_location_1.end_date = self.reference_date - datetime.timedelta(days=1)
        self.pickup_location_1.save()
        names = self._list_pickup_location_names("pickup_locations:public_pickup_locations-list")
        self.assertEqual(["pickup_location_name_2", "pickup_location_name_3"], names)

    def test_publicList_plWithFutureStartDate_isExcluded(self):
        self.pickup_location_1.start_date = self.reference_date + datetime.timedelta(days=1)
        self.pickup_location_1.save()
        names = self._list_pickup_location_names("pickup_locations:public_pickup_locations-list")
        self.assertEqual(["pickup_location_name_2", "pickup_location_name_3"], names)

    def test_publicList_plActiveWithinWindow_isIncluded(self):
        self.pickup_location_1.start_date = self.reference_date - datetime.timedelta(days=10)
        self.pickup_location_1.end_date = self.reference_date + datetime.timedelta(days=10)
        self.pickup_location_2.end_date = self.reference_date - datetime.timedelta(days=1)
        self.pickup_location_1.save()
        self.pickup_location_2.save()
        names = self._list_pickup_location_names("pickup_locations:public_pickup_locations-list")
        self.assertEqual(["pickup_location_name_1", "pickup_location_name_3"], names)

    def test_capacityCheck_includesFutureStartDatePickupLocationAsCandidate(self):
        self.pickup_location_1.end_date = self.reference_date - datetime.timedelta(days=1)
        self.pickup_location_3.start_date = self.reference_date + datetime.timedelta(days=30)
        self.pickup_location_1.save()
        self.pickup_location_3.save()

        with patch.object(
            PickupLocationCapacityGeneralChecker,
            "does_pickup_location_have_enough_capacity_to_add_subscriptions",
            return_value=True,
        ):
            response = self.client.post(
                reverse("pickup_locations:pickup_location_capacity_check"),
                data={"shopping_cart": {}, "growing_period_id": None},
                content_type="application/json",
            )

        self.assertStatusCode(response, status.HTTP_200_OK)
        ids = response.json()["pickup_location_ids_with_enough_capacity_for_order"]
        self.assertIn(self.pickup_location_2.id, ids)
        self.assertIn(self.pickup_location_3.id, ids)
        self.assertNotIn(self.pickup_location_1.id, ids)
