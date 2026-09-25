from django.urls import reverse
from rest_framework import status

from tapir.bakery.models import BreadCapacityPickupLocation
from tapir.bakery.serializers import MAX_PIECES_PER_ENTRY
from tapir.bakery.tests.factories import (
    BreadCapacityPickupLocationFactory,
    BreadFactory,
)
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

YEAR = 2026
WEEK = 11
DAY = 4


class TestBreadCapacityAllocationView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))
        self.url = reverse("bakery:bread-capacity-allocations")

    def get(self, **overrides):
        params = {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY}
        params.update(overrides)
        return self.client.get(self.url, params)

    def post(self, updates):
        return self.client.post(
            self.url,
            data={"year": YEAR, "delivery_week": WEEK, "updates": updates},
            content_type="application/json",
        )

    def test_get_default_returnsOneEntryPerStationDeliveredThatDay(self):
        delivered_that_day = create_pickup_location_with_opening_times(
            [DAY], name="Hofladen"
        )
        create_pickup_location_with_opening_times([1], name="Marktstand")
        bread = BreadFactory.create(name="Roggenbrot")
        BreadCapacityPickupLocationFactory.create(
            bread=bread,
            pickup_location=delivered_that_day,
            year=YEAR,
            delivery_week=WEEK,
            capacity=5,
        )

        response = self.get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [entry["name"] for entry in response.data["pickup_locations"]],
            ["Hofladen"],
        )
        self.assertEqual(
            response.data["allocations"],
            {str(delivered_that_day.id): {str(bread.id): 5}},
        )

    def test_get_otherWeek_isNotIncluded(self):
        pickup_location = create_pickup_location_with_opening_times([DAY])
        BreadCapacityPickupLocationFactory.create(
            bread=BreadFactory.create(name="Roggenbrot"),
            pickup_location=pickup_location,
            year=YEAR,
            delivery_week=WEEK + 1,
            capacity=5,
        )

        response = self.get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["allocations"], {str(pickup_location.id): {}})

    def test_get_missingDeliveryDay_returns400(self):
        response = self.client.get(self.url, {"year": YEAR, "delivery_week": WEEK})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_nonNumericParameter_returns400(self):
        response = self.get(delivery_day="Freitag")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_plainMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        response = self.get()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_newCapacity_isCreated(self):
        pickup_location = create_pickup_location_with_opening_times([DAY])
        bread = BreadFactory.create(name="Roggenbrot")

        response = self.post(
            [
                {
                    "pickup_location": str(pickup_location.id),
                    "bread": str(bread.id),
                    "capacity": 10,
                }
            ]
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            BreadCapacityPickupLocation.objects.get(
                year=YEAR,
                delivery_week=WEEK,
                pickup_location=pickup_location,
                bread=bread,
            ).capacity,
            10,
        )

    def test_post_existingCapacity_isUpdated(self):
        pickup_location = create_pickup_location_with_opening_times([DAY])
        bread = BreadFactory.create(name="Roggenbrot")
        BreadCapacityPickupLocationFactory.create(
            bread=bread,
            pickup_location=pickup_location,
            year=YEAR,
            delivery_week=WEEK,
            capacity=5,
        )

        response = self.post(
            [
                {
                    "pickup_location": str(pickup_location.id),
                    "bread": str(bread.id),
                    "capacity": 20,
                }
            ]
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            BreadCapacityPickupLocation.objects.get(
                year=YEAR,
                delivery_week=WEEK,
                pickup_location=pickup_location,
                bread=bread,
            ).capacity,
            20,
        )

    def test_post_nullCapacity_deletesTheRow(self):
        pickup_location = create_pickup_location_with_opening_times([DAY])
        bread = BreadFactory.create(name="Roggenbrot")
        BreadCapacityPickupLocationFactory.create(
            bread=bread,
            pickup_location=pickup_location,
            year=YEAR,
            delivery_week=WEEK,
            capacity=5,
        )

        response = self.post(
            [
                {
                    "pickup_location": str(pickup_location.id),
                    "bread": str(bread.id),
                    "capacity": None,
                }
            ]
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(BreadCapacityPickupLocation.objects.exists())

    def test_post_negativeCapacity_returns400(self):
        # The column carries CHECK (capacity >= 0).
        pickup_location = create_pickup_location_with_opening_times([DAY])
        bread = BreadFactory.create(name="Roggenbrot")

        response = self.post(
            [
                {
                    "pickup_location": str(pickup_location.id),
                    "bread": str(bread.id),
                    "capacity": -5,
                }
            ]
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(BreadCapacityPickupLocation.objects.exists())

    def test_post_capacityAboveThePlausibilityLimit_returns400(self):
        pickup_location = create_pickup_location_with_opening_times([DAY])
        bread = BreadFactory.create(name="Roggenbrot")

        response = self.post(
            [
                {
                    "pickup_location": str(pickup_location.id),
                    "bread": str(bread.id),
                    "capacity": MAX_PIECES_PER_ENTRY + 1,
                }
            ]
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(BreadCapacityPickupLocation.objects.exists())

    def test_post_missingYearAndWeek_returns400(self):
        response = self.client.post(
            self.url, data={"updates": []}, content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_plainMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        response = self.post([])

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
