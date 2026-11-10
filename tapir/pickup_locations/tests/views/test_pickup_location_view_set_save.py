import datetime
from decimal import Decimal

from django.http import HttpResponse
from django.urls import reverse
from rest_framework import status

from tapir.pickup_locations.services.pickup_location_validator import (
    PickupLocationValidator,
)
from tapir.wirgarten.models import PickupLocation, PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.pickup_location_date_validation import (
    PICKUP_LOCATION_START_DATE_VALIDATION_MESSAGE,
)
from tapir.wirgarten.tests.factories import (
    LocationRouteFactory,
    MemberFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationViewSetSave(TapirIntegrationTest):
    @staticmethod
    def _build_request_data(**overrides) -> dict:
        data = {
            "name": "Test Abholort",
            "latitude": "48.1",
            "longitude": "11.5",
            "street": "Musterstraße 1",
            "postcode": "12345",
            "city": "Musterstadt",
            "start_date": "2026-01-05",
            "end_date": "2026-12-27",
            "opening_times": [
                {"day_of_week": 1, "open_time": "14:00", "close_time": "18:00"},
                {"day_of_week": 3, "open_time": "08:00", "close_time": "09:30"},
            ],
        }
        data.update(overrides)
        return data

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._login_as_admin()

    def _create(self, data: dict) -> HttpResponse:
        return self.client.post(
            reverse("pickup_locations:pickup_locations-list"),
            data=data,
            content_type="application/json",
        )

    def _update(self, pickup_location_id: str, data: dict) -> HttpResponse:
        return self.client.put(
            reverse(
                "pickup_locations:pickup_locations-detail",
                kwargs={"pk": pickup_location_id},
            ),
            data=data,
            content_type="application/json",
        )

    def test_create_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self._create(self._build_request_data())

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(PickupLocation.objects.exists())

    def test_create_validData_createsPickupLocationWithOpeningTimes(self):
        location_route = LocationRouteFactory.create()

        response = self._create(
            self._build_request_data(
                location_route_id=location_route.id,
                show_details_in_basket_totals_export=True,
            )
        )

        self.assertStatusCode(response, status.HTTP_201_CREATED)
        pickup_location = PickupLocation.objects.get()
        self.assertEqual(pickup_location.id, response.json()["id"])
        self.assertEqual("Test Abholort", pickup_location.name)
        self.assertEqual(Decimal("48.1"), pickup_location.latitude)
        self.assertEqual(Decimal("11.5"), pickup_location.longitude)
        self.assertEqual(location_route, pickup_location.location_route)
        self.assertTrue(pickup_location.show_details_in_basket_totals_export)
        self.assertEqual(datetime.date(2026, 1, 5), pickup_location.start_date)
        self.assertEqual(datetime.date(2026, 12, 27), pickup_location.end_date)
        self.assertEqual(
            [
                (1, datetime.time(14, 0), datetime.time(18, 0)),
                (3, datetime.time(8, 0), datetime.time(9, 30)),
            ],
            list(
                PickupLocationOpeningTime.objects.filter(
                    pickup_location=pickup_location
                )
                .order_by("day_of_week")
                .values_list("day_of_week", "open_time", "close_time")
            ),
        )
        self.assertEqual(1, response.json()["delivery_day"])
        self.assertEqual(2, len(response.json()["opening_times"]))

    def test_create_homeDeliveryWithoutCoordinates_createsPickupLocation(self):
        response = self._create(
            self._build_request_data(
                is_home_delivery=True, longitude=None, latitude=None
            )
        )

        self.assertStatusCode(response, status.HTTP_201_CREATED)
        pickup_location = PickupLocation.objects.get()
        self.assertTrue(pickup_location.is_home_delivery)
        self.assertIsNone(pickup_location.longitude)
        self.assertIsNone(pickup_location.latitude)

    def test_create_invalidData_returns400AndCreatesNothing(self):
        response = self._create(self._build_request_data(start_date="2026-01-06"))

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            {"start_date": PICKUP_LOCATION_START_DATE_VALIDATION_MESSAGE},
            response.json(),
        )
        self.assertFalse(PickupLocation.objects.exists())

    def test_update_validData_updatesFieldsAndReplacesOpeningTimes(self):
        pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=pickup_location,
            day_of_week=0,
            open_time=datetime.time(10, 0),
            close_time=datetime.time(12, 0),
        )

        response = self._update(
            pickup_location.id,
            self._build_request_data(
                name="Neuer Name",
                start_date=None,
                end_date=None,
                opening_times=[
                    {"day_of_week": 4, "open_time": "15:00", "close_time": "19:00"}
                ],
            ),
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        pickup_location.refresh_from_db()
        self.assertEqual("Neuer Name", pickup_location.name)
        self.assertIsNone(pickup_location.start_date)
        self.assertIsNone(pickup_location.end_date)
        self.assertEqual(
            [(4, datetime.time(15, 0), datetime.time(19, 0))],
            list(
                PickupLocationOpeningTime.objects.filter(
                    pickup_location=pickup_location
                ).values_list("day_of_week", "open_time", "close_time")
            ),
        )

    def test_update_invalidData_returns400AndKeepsPickupLocation(self):
        pickup_location = PickupLocationFactory.create(name="Alter Name")

        response = self._update(
            pickup_location.id,
            self._build_request_data(name="Neuer Name", opening_times=[]),
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            {"opening_times": PickupLocationValidator.NO_OPENING_TIMES_MESSAGE},
            response.json(),
        )
        pickup_location.refresh_from_db()
        self.assertEqual("Alter Name", pickup_location.name)

    def test_update_unknownPickupLocation_returns404(self):
        response = self._update("unknown", self._build_request_data())

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)
