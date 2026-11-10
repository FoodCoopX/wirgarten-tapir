import datetime

from django.http import HttpResponse
from django.urls import reverse
from rest_framework import status

from tapir.pickup_locations.services.pickup_location_deletion_validator import (
    PickupLocationDeletionValidator,
)
from tapir.wirgarten.models import PickupLocation, PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationViewSetDestroy(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._login_as_admin()
        self.pickup_location = PickupLocationFactory.create()

    def _destroy(self, pickup_location_id: str) -> HttpResponse:
        return self.client.delete(
            reverse(
                "pickup_locations:pickup_locations-detail",
                kwargs={"pk": pickup_location_id},
            )
        )

    def test_destroy_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self._destroy(self.pickup_location.id)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            PickupLocation.objects.filter(id=self.pickup_location.id).exists()
        )

    def test_destroy_unusedLocation_deletesLocationAndOpeningTimes(self):
        PickupLocationOpeningTime.objects.create(
            pickup_location=self.pickup_location,
            day_of_week=1,
            open_time=datetime.time(14, 0),
            close_time=datetime.time(18, 0),
        )

        response = self._destroy(self.pickup_location.id)

        self.assertStatusCode(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PickupLocation.objects.exists())
        self.assertFalse(PickupLocationOpeningTime.objects.exists())

    def test_destroy_locationInUse_returns400AndKeepsLocation(self):
        MemberPickupLocationFactory.create(pickup_location=self.pickup_location)

        response = self._destroy(self.pickup_location.id)

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            PickupLocationDeletionValidator.IN_USE_MESSAGE.format(usages="Mitgliedern"),
            response.json(),
        )
        self.assertTrue(
            PickupLocation.objects.filter(id=self.pickup_location.id).exists()
        )

    def test_destroy_unknownLocation_returns404(self):
        response = self._destroy("unknown")

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)
