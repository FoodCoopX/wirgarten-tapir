from tapir.pickup_locations.templatetags.pickup_locations import (
    sum_pickup_location_basket_totals,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest

ENTRIES = [
    {
        "route_name": "Runde 3",
        "route_basket_totals": {
            "totals": {"small": 4, "normal": 2},
            "pickup_location_data": [
                {"name": "Bad Heilbrunn", "totals": {"small": 2, "normal": 1}},
                {"name": "Penzberg", "totals": {"small": 1, "normal": 1}},
                {"name": "Tutzing", "totals": {"small": 1, "normal": 0}},
            ],
        },
    },
    {
        "route_name": "Runde 4",
        "route_basket_totals": {
            "totals": {"small": 3, "normal": 1},
            "pickup_location_data": [
                {"name": "Biotop intern", "totals": {"small": 2, "normal": 1}},
                {"name": "Spende Tafel", "totals": {"small": 1}},
            ],
        },
    },
]


class TestSumPickupLocationBasketTotals(TapirUnitTest):
    def test_sumPickupLocationBasketTotals_multipleRoutes_sumsMatchingNames(self):
        context = {"entries": ENTRIES}

        result = sum_pickup_location_basket_totals(
            context, "small", "Bad Heilbrunn", "Penzberg", "Biotop intern"
        )

        self.assertEqual(5, result)

    def test_sumPickupLocationBasketTotals_subsetOfNames_sumsOnlyThoseLocations(self):
        context = {"entries": ENTRIES}

        result = sum_pickup_location_basket_totals(
            context, "small", "Bad Heilbrunn", "Penzberg"
        )

        self.assertEqual(3, result)

    def test_sumPickupLocationBasketTotals_unknownName_countsAsZero(self):
        context = {"entries": ENTRIES}

        result = sum_pickup_location_basket_totals(
            context, "small", "Bad Heilbrunn", "Unbekannt"
        )

        self.assertEqual(2, result)

    def test_sumPickupLocationBasketTotals_missingHeader_countsAsZero(self):
        context = {"entries": ENTRIES}

        result = sum_pickup_location_basket_totals(context, "xlarge", "Spende Tafel")

        self.assertEqual(0, result)
