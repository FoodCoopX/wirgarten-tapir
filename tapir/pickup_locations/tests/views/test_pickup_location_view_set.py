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
        self.pl_1 = PickupLocationFactory.create(name="pl_name_1")
        self.pl_2 = PickupLocationFactory.create(name="pl_name_2")
        self.pl_3 = PickupLocationFactory.create(name="pl_name_3")
        self._login_as_admin()
        self.reference_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=datetime.date.today(),
            apply_buffer_time=False,
            cache={},
        )

    def _list(self, url_name):
        url = reverse(url_name)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        return sorted(loc["name"] for loc in response.json())

    def test_adminList_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        response = self.client.get(reverse("pickup_locations:pickup_locations-list"))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_adminList_returnsAllPickupLocationsRegardlessOfDates(self):
        self.pl_1.end_date = self.reference_date - datetime.timedelta(days=1)
        self.pl_2.start_date = self.reference_date + datetime.timedelta(days=1)
        self.pl_1.save()
        self.pl_2.save()
        names = self._list("pickup_locations:pickup_locations-list")
        self.assertEqual(["pl_name_1", "pl_name_2", "pl_name_3"], names)

    def test_publicList_noDates_returnsAllPickupLocations(self):
        names = self._list("pickup_locations:public_pickup_locations-list")
        self.assertEqual(["pl_name_1", "pl_name_2", "pl_name_3"], names)

    def test_publicList_plWithPastEndDate_isExcluded(self):
        self.pl_1.end_date = self.reference_date - datetime.timedelta(days=1)
        self.pl_1.save()
        names = self._list("pickup_locations:public_pickup_locations-list")
        self.assertEqual(["pl_name_2", "pl_name_3"], names)

    def test_publicList_plWithFutureStartDate_isExcluded(self):
        self.pl_1.start_date = self.reference_date + datetime.timedelta(days=1)
        self.pl_1.save()
        names = self._list("pickup_locations:public_pickup_locations-list")
        self.assertEqual(["pl_name_2", "pl_name_3"], names)

    def test_publicList_plActiveWithinWindow_isIncluded(self):
        self.pl_1.start_date = self.reference_date - datetime.timedelta(days=10)
        self.pl_1.end_date = self.reference_date + datetime.timedelta(days=10)
        self.pl_2.end_date = self.reference_date - datetime.timedelta(days=1)
        self.pl_1.save()
        self.pl_2.save()
        names = self._list("pickup_locations:public_pickup_locations-list")
        self.assertEqual(["pl_name_1", "pl_name_3"], names)

    def test_capacityCheck_includesFutureStartDatePickupLocationAsCandidate(self):
        self.pl_1.end_date = self.reference_date - datetime.timedelta(days=1)
        self.pl_3.start_date = self.reference_date + datetime.timedelta(days=30)
        self.pl_1.save()
        self.pl_3.save()

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

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        ids = response.json()["pickup_location_ids_with_enough_capacity_for_order"]
        self.assertIn(self.pl_2.id, ids)
        self.assertIn(self.pl_3.id, ids)
        self.assertNotIn(self.pl_1.id, ids)
