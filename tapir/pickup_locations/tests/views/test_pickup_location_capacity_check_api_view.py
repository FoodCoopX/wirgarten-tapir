import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status

from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    monday_after,
    sunday_before,
)


class TestPickupLocationCapacityCheckApiView(TapirIntegrationTest):
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

    @patch.object(
        PickupLocationCapacityGeneralChecker,
        "does_pickup_location_have_enough_capacity_to_add_subscriptions",
        return_value=True,
    )
    def test_capacityCheck_futureStartDatePickupLocationNotCandidate_excludesItFromCandidates(
        self, mock_does_pickup_location_have_enough_capacity_to_add_subscriptions: Mock
    ):
        self.pickup_location_1.end_date = sunday_before(self.reference_date)
        self.pickup_location_3.start_date = monday_after(self.reference_date)
        self.pickup_location_1.save()
        self.pickup_location_3.save()

        response = self.client.post(
            reverse("pickup_locations:pickup_location_capacity_check"),
            data={"shopping_cart": {}, "growing_period_id": None},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        ids = response.json()["pickup_location_ids_with_enough_capacity_for_order"]
        self.assertIn(self.pickup_location_2.id, ids)
        self.assertNotIn(self.pickup_location_3.id, ids)
        self.assertNotIn(self.pickup_location_1.id, ids)
