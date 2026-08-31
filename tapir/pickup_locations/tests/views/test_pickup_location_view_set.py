import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.models import PickupLocationGrowingPeriod
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
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

    @staticmethod
    def _create_growing_period(start_date, end_date):
        return GrowingPeriodFactory.create(start_date=start_date, end_date=end_date)

    def _list_pickup_locations(self, growing_period_id=None):
        url = reverse("pickup_locations:pickup_locations-list")
        if growing_period_id:
            url += f"?growing_period_id={growing_period_id}"
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        return sorted(loc["name"] for loc in response.json())

    def test_list_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        response = self.client.get(reverse("pickup_locations:pickup_locations-list"))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_list_flagOff_returnsAllPickupLocations(self):
        names = self._list_pickup_locations()
        self.assertEqual(["pl_name_1", "pl_name_2", "pl_name_3"], names)

    def test_list_flagOn_filtersByActiveGrowingPeriod(self):
        today = datetime.date.today()
        active_gp = self._create_growing_period(
            start_date=today - datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=10),
        )
        inactive_gp = self._create_growing_period(
            start_date=today + datetime.timedelta(days=100),
            end_date=today + datetime.timedelta(days=200),
        )
        PickupLocationGrowingPeriod.objects.create(
            pickup_location=self.pl_1, growing_period=active_gp
        )
        PickupLocationGrowingPeriod.objects.create(
            pickup_location=self.pl_2, growing_period=inactive_gp
        )

        self._set_parameter(ParameterKeys.PICKUP_LOCATION_GROWING_PERIOD_ENABLED, True)
        names = self._list_pickup_locations()
        self.assertEqual(["pl_name_1"], names)

    def test_list_flagOn_explicitGrowingPeriodId(self):
        today = datetime.date.today()
        gp_1 = self._create_growing_period(
            start_date=today - datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=10),
        )
        gp_2 = self._create_growing_period(
            start_date=today + datetime.timedelta(days=50),
            end_date=today + datetime.timedelta(days=100),
        )
        PickupLocationGrowingPeriod.objects.create(
            pickup_location=self.pl_1, growing_period=gp_1
        )
        PickupLocationGrowingPeriod.objects.create(
            pickup_location=self.pl_2, growing_period=gp_2
        )

        self._set_parameter(ParameterKeys.PICKUP_LOCATION_GROWING_PERIOD_ENABLED, True)
        names = self._list_pickup_locations(growing_period_id=str(gp_2.id))
        self.assertEqual(["pl_name_2"], names)

    def test_list_flagOn_noActiveGrowingPeriod_returnsEmpty(self):
        today = datetime.date.today()
        past_gp = self._create_growing_period(
            start_date=today - datetime.timedelta(days=40),
            end_date=today - datetime.timedelta(days=20),
        )
        PickupLocationGrowingPeriod.objects.create(
            pickup_location=self.pl_1, growing_period=past_gp
        )

        self._set_parameter(ParameterKeys.PICKUP_LOCATION_GROWING_PERIOD_ENABLED, True)
        names = self._list_pickup_locations()
        self.assertEqual([], names)
