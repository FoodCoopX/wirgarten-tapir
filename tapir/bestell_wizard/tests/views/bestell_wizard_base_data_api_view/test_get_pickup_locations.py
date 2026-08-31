import datetime

from django.urls import reverse

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestBestellWizardBaseDataPickupLocations(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, now=datetime.datetime(year=2024, month=6, day=8))
        GrowingPeriodFactory.create(start_date=datetime.date(year=2024, month=1, day=1))

    def test_get_includesFutureStartDatePickupLocationAndExcludesDecommissioned(self):
        active = PickupLocationFactory.create(name="active")
        future = PickupLocationFactory.create(
            name="future", start_date=datetime.date(year=2024, month=8, day=1)
        )
        decommissioned = PickupLocationFactory.create(
            name="decommissioned", end_date=datetime.date(year=2024, month=6, day=1)
        )

        response = self.client.get(reverse("bestell_wizard:bestell_wizard_base_data"))
        self.assertEqual(200, response.status_code)

        names = [pl["name"] for pl in response.json()["pickup_locations"]]
        self.assertIn(active.name, names)
        self.assertIn(future.name, names)
        self.assertNotIn(decommissioned.name, names)
