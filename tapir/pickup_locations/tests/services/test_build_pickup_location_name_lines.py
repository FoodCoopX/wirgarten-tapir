from tapir.pickup_locations.services.location_route_column_provider import (
    LocationRouteColumnProvider,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildPickupLocationNameLines(TapirUnitTest):
    def test_buildPickupLocationNameLines_noNames_returnsEmptyList(self):
        result = LocationRouteColumnProvider.build_pickup_location_name_lines([])

        self.assertEqual([], result)

    def test_buildPickupLocationNameLines_threeNames_returnsSingleLine(self):
        result = LocationRouteColumnProvider.build_pickup_location_name_lines(
            ["Hofpunkt", "Grünes Warenhaus", "Hochalmstraße"]
        )

        self.assertEqual(["Hofpunkt, Grünes Warenhaus, Hochalmstraße"], result)

    def test_buildPickupLocationNameLines_fourNames_splitsIntoTwoLines(self):
        result = LocationRouteColumnProvider.build_pickup_location_name_lines(
            ["A", "B", "C", "D"]
        )

        self.assertEqual(["A, B,", "C, D"], result)

    def test_buildPickupLocationNameLines_fiveNames_firstLineGetsTheExtraName(self):
        result = LocationRouteColumnProvider.build_pickup_location_name_lines(
            ["A", "B", "C", "D", "E"]
        )

        self.assertEqual(["A, B, C,", "D, E"], result)
