import datetime
import json
from unittest import mock

from tapir.wirgarten.forms import pickup_location as pickup_location_module
from tapir.wirgarten.forms.pickup_location import get_pickup_locations_map_data
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationConfig(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getPickupLocationsMapData_default_serializesDateBoundariesCorrectly(self):
        pickup_location = PickupLocationFactory.create(
            name="pickup_location_with_dates",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
        )
        data = json.loads(get_pickup_locations_map_data([pickup_location], [], {}))
        self.assertEqual("2026-01-01", data[pickup_location.id]["start_date"])
        self.assertEqual("2026-12-31", data[pickup_location.id]["end_date"])

    def test_getPickupLocationsMapData_missingDates_serializesAsNull(self):
        pickup_location = PickupLocationFactory.create(name="pl_without_dates")
        data = json.loads(get_pickup_locations_map_data([pickup_location], [], {}))
        self.assertIsNone(data[pickup_location.id]["start_date"])
        self.assertIsNone(data[pickup_location.id]["end_date"])

    def test_getPickupLocationsMapData_unexpectedValue_raisesTypeError(self):
        pickup_location = PickupLocationFactory.create(name="pl_with_non_serializable")
        with mock.patch.object(
            pickup_location_module,
            "pickup_location_to_dict",
            return_value={"x": object()},
        ):
            with self.assertRaises(TypeError):
                get_pickup_locations_map_data([pickup_location], [], {})
