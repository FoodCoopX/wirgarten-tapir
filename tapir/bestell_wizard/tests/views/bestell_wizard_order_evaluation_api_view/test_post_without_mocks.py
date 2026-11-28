import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


# Smoke test: test_post.py mocks the services, this checks the view and services fit together.
class TestPostWithoutMocks(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, now=datetime.datetime(year=2026, month=6, day=1))

    def test_post_productFullInSelectedPeriod_returnsEveryField(self):
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2027, month=1, day=1)
        )
        product = ProductFactory.create(capacity=10, type__delivery_cycle=WEEKLY[0])
        ProductCapacityFactory.create(
            product_type=product.type, period=growing_period, capacity=10
        )
        ProductPriceFactory.create(
            product=product, size=1, valid_from=growing_period.start_date
        )
        SubscriptionFactory.create(period=growing_period, product=product, quantity=10)
        pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=pickup_location,
            day_of_week=3,
            open_time=datetime.time(8, 0),
            close_time=datetime.time(9, 0),
        )

        response = self.client.post(
            reverse("bestell_wizard:order_evaluation"),
            data={
                "shopping_cart": {product.id: 1},
                "growing_period_id": growing_period.id,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {
                "ids_of_product_types_over_capacity": [product.type.id],
                "ids_of_products_over_capacity": [product.id],
                "pickup_location_ids_with_enough_capacity_for_order": [
                    pickup_location.id
                ],
                "delivery_date_by_pickup_location_id_and_product_type_id": {
                    pickup_location.id: {product.type.id: "2027-01-07"}
                },
            },
            response.json(),
        )
