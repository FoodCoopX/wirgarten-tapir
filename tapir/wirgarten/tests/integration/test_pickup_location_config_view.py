import datetime

from django.test import RequestFactory

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.views.pickup_location_config import PickupLocationCfgView


class TestPickupLocationCfgView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.active = PickupLocationFactory.create(name="active")
        self.future = PickupLocationFactory.create(
            name="future", start_date=datetime.date(2099, 1, 1)
        )
        self.decommissioned = PickupLocationFactory.create(
            name="decommissioned", end_date=datetime.date(2000, 1, 1)
        )

    def _filtered_names(self, **query):
        view = PickupLocationCfgView()
        view.request = RequestFactory().get("/tapir/admin/pickuplocations/", query)
        return {pl.name for pl in view.get_filtered_pickup_locations()}

    def test_getFilteredPickupLocations_default_returnsCurrentAndFutureButNotEnded(self):
        self.assertEqual({"active", "future"}, self._filtered_names())

    def test_getFilteredPickupLocations_showEnded_includesDecommissioned(self):
        self.assertEqual(
            {"active", "future", "decommissioned"},
            self._filtered_names(show_ended="on"),
        )

    def test_getFilteredPickupLocations_searchByName_returnsMatchingPickupLocation(self):
        self.assertEqual({"active"}, self._filtered_names(search="active"))

    def test_getFilteredPickupLocations_searchByStreet_returnsMatchingPickupLocation(self):
        PickupLocationFactory.create(name="other", street="Sonnenweg 2")
        self.assertEqual({"other"}, self._filtered_names(search="Sonnenweg"))
