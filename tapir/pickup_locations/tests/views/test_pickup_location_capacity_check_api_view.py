import datetime
from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status

from tapir.pickup_locations.services.pickup_locations_with_enough_capacity_provider import (
    PickupLocationsWithEnoughCapacityProvider,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


@patch.object(
    PickupLocationsWithEnoughCapacityProvider,
    "get_pickup_location_ids",
    autospec=True,
    return_value=["id_1", "id_2"],
)
class TestPickupLocationCapacityCheckApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, now=datetime.datetime(year=2026, month=6, day=1))

    def test_post_growingPeriodGiven_usesContractStartDateInThatPeriod(
        self, mock_get_pickup_location_ids: MagicMock
    ):
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2027, month=1, day=1)
        )

        response = self.client.post(
            reverse("pickup_locations:pickup_location_capacity_check"),
            data={"shopping_cart": {}, "growing_period_id": growing_period.id},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            ["id_1", "id_2"],
            response.json()["pickup_location_ids_with_enough_capacity_for_order"],
        )
        mock_get_pickup_location_ids.assert_called_once()
        self.assertEqual(
            datetime.date(year=2027, month=1, day=4),
            mock_get_pickup_location_ids.call_args.kwargs["subscription_start"],
        )

    def test_post_noGrowingPeriod_usesNextContractStartDate(
        self, mock_get_pickup_location_ids: MagicMock
    ):
        response = self.client.post(
            reverse("pickup_locations:pickup_location_capacity_check"),
            data={"shopping_cart": {}, "growing_period_id": None},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        mock_get_pickup_location_ids.assert_called_once()
        self.assertEqual(
            datetime.date(year=2026, month=6, day=8),
            mock_get_pickup_location_ids.call_args.kwargs["subscription_start"],
        )
