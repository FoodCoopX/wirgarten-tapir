import datetime

from django.urls import reverse
from rest_framework import status

from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    monday_after,
    sunday_before,
)


class TestPickupLocationViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.pickup_location_1 = PickupLocationFactory.create(
            name="pickup_location_name_1"
        )
        self.pickup_location_2 = PickupLocationFactory.create(
            name="pickup_location_name_2"
        )
        self.pickup_location_3 = PickupLocationFactory.create(
            name="pickup_location_name_3"
        )
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
        self.pickup_location_1.end_date = sunday_before(self.reference_date)
        self.pickup_location_2.start_date = monday_after(self.reference_date)
        self.pickup_location_1.save()
        self.pickup_location_2.save()
        names = self._list_pickup_location_names(
            "pickup_locations:pickup_locations-list"
        )
        self.assertEqual(
            [
                "pickup_location_name_1",
                "pickup_location_name_2",
                "pickup_location_name_3",
            ],
            names,
        )
