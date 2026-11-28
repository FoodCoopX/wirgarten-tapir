import datetime
from unittest.mock import patch, MagicMock

from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.pickup_locations.services.pickup_locations_with_enough_capacity_provider import (
    PickupLocationsWithEnoughCapacityProvider,
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


class TestGetPickupLocationIds(TapirIntegrationTest):
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
        self.reference_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=datetime.date.today(),
            apply_buffer_time=False,
            cache={},
        )

    @patch.object(
        PickupLocationCapacityGeneralChecker,
        "does_pickup_location_have_enough_capacity_to_add_subscriptions",
        autospec=True,
        return_value=True,
    )
    def test_getPickupLocationIds_pickupLocationsNotActiveAtSubscriptionStart_excludesThem(
        self, _: MagicMock
    ):
        self.pickup_location_1.end_date = sunday_before(self.reference_date)
        self.pickup_location_3.start_date = monday_after(self.reference_date)
        self.pickup_location_1.save()
        self.pickup_location_3.save()

        ids = PickupLocationsWithEnoughCapacityProvider.get_pickup_location_ids(
            order={}, subscription_start=self.reference_date, cache={}
        )

        self.assertEqual([self.pickup_location_2.id], ids)

    @patch.object(
        PickupLocationCapacityGeneralChecker,
        "does_pickup_location_have_enough_capacity_to_add_subscriptions",
        autospec=True,
    )
    def test_getPickupLocationIds_pickupLocationWithoutEnoughCapacity_excludesIt(
        self, mock_does_pickup_location_have_enough_capacity: MagicMock
    ):
        mock_does_pickup_location_have_enough_capacity.side_effect = (
            lambda pickup_location, **_: pickup_location != self.pickup_location_2
        )

        ids = PickupLocationsWithEnoughCapacityProvider.get_pickup_location_ids(
            order={}, subscription_start=self.reference_date, cache={}
        )

        self.assertEqual(
            {self.pickup_location_1.id, self.pickup_location_3.id}, set(ids)
        )
