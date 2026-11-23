import datetime
from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status

from tapir.bestell_wizard.services.first_delivery_dates_provider import (
    FirstDeliveryDatesProvider,
)
from tapir.bestell_wizard.services.products_over_capacity_for_order_provider import (
    ProductsOverCapacityForOrderProvider,
)
from tapir.pickup_locations.services.pickup_locations_with_enough_capacity_provider import (
    PickupLocationsWithEnoughCapacityProvider,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import GrowingPeriodFactory, ProductFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


@patch.object(
    FirstDeliveryDatesProvider,
    "get_delivery_date_by_pickup_location_id_and_product_type_id",
    autospec=True,
    return_value={"pickup_location_id": {"product_type_id": datetime.date(2027, 1, 7)}},
)
@patch.object(
    PickupLocationsWithEnoughCapacityProvider,
    "get_pickup_location_ids",
    autospec=True,
    return_value=["pickup_location_id"],
)
@patch.object(
    ProductsOverCapacityForOrderProvider,
    "get_product_ids",
    autospec=True,
    return_value=["product_id"],
)
@patch.object(
    ProductsOverCapacityForOrderProvider,
    "get_product_type_ids",
    autospec=True,
    return_value=["product_type_id"],
)
class TestPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, now=datetime.datetime(year=2026, month=6, day=1))
        self.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2027, month=1, day=1)
        )
        self.product = ProductFactory.create()

    def test_post_default_returnsProductTypeIdsOverCapacity(
        self,
        mock_get_product_type_ids: MagicMock,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
    ):
        response_data = self._post()

        self.assertEqual(
            ["product_type_id"], response_data["ids_of_product_types_over_capacity"]
        )
        self._assert_called_with_order_and_contract_start_date(
            mock_get_product_type_ids
        )

    def test_post_default_returnsProductIdsOverCapacity(
        self,
        _: MagicMock,
        mock_get_product_ids: MagicMock,
        __: MagicMock,
        ___: MagicMock,
    ):
        response_data = self._post()

        self.assertEqual(["product_id"], response_data["ids_of_products_over_capacity"])
        self._assert_called_with_order_and_contract_start_date(mock_get_product_ids)

    def test_post_default_returnsPickupLocationIdsWithEnoughCapacity(
        self,
        _: MagicMock,
        __: MagicMock,
        mock_get_pickup_location_ids: MagicMock,
        ___: MagicMock,
    ):
        response_data = self._post()

        self.assertEqual(
            ["pickup_location_id"],
            response_data["pickup_location_ids_with_enough_capacity_for_order"],
        )
        mock_get_pickup_location_ids.assert_called_once()
        call_kwargs = mock_get_pickup_location_ids.call_args.kwargs
        self.assertEqual({self.product: 2}, call_kwargs["order"])
        self.assertEqual(
            datetime.date(year=2027, month=1, day=4), call_kwargs["subscription_start"]
        )

    def test_post_default_returnsFirstDeliveryDates(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        mock_get_delivery_dates: MagicMock,
    ):
        response_data = self._post()

        self.assertEqual(
            {"pickup_location_id": {"product_type_id": "2027-01-07"}},
            response_data["delivery_date_by_pickup_location_id_and_product_type_id"],
        )
        self._assert_called_with_order_and_contract_start_date(mock_get_delivery_dates)

    def _post(self) -> dict:
        response = self.client.post(
            reverse("bestell_wizard:order_evaluation"),
            data={
                "shopping_cart": {self.product.id: 2},
                "growing_period_id": self.growing_period.id,
            },
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        return response.json()

    def _assert_called_with_order_and_contract_start_date(self, mock: MagicMock):
        mock.assert_called_once()
        call_kwargs = mock.call_args.kwargs
        self.assertEqual({self.product: 2}, call_kwargs["order"])
        self.assertEqual(
            datetime.date(year=2027, month=1, day=4),
            call_kwargs["contract_start_date"],
        )
