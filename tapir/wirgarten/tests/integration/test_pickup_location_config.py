import datetime
import json

from tapir.wirgarten.forms.pickup_location import get_pickup_locations_map_data
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationConfig(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_pickup_locations_map_data_serializesDates(self):
        pl = PickupLocationFactory.create(
            name="pl_with_dates",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
        )
        data = json.loads(get_pickup_locations_map_data([pl], [], {}))
        self.assertEqual("2026-01-01", data[pl.id]["start_date"])
        self.assertEqual("2026-12-31", data[pl.id]["end_date"])
