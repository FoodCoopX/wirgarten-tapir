from tapir.pickup_locations.templatetags.pickup_locations import (
    sum_location_route_basket_totals,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest

ENTRIES = [
    {
        "route_name": "Runde 3",
        "route_basket_totals": {
            "totals": {"small": 4, "normal": 2},
        },
    },
    {
        "route_name": "Runde 4",
        "route_basket_totals": {
            "totals": {"small": 3, "normal": 1},
        },
    },
]


class TestSumLocationRouteBasketTotals(TapirUnitTest):
    def test_sumLocationRouteBasketTotals_multipleRoutes_sumsMatchingNames(self):
        context = {"entries": ENTRIES}

        result = sum_location_route_basket_totals(
            context, "small", "Runde 3", "Runde 4"
        )

        self.assertEqual(7, result)

    def test_sumLocationRouteBasketTotals_subsetOfNames_sumsOnlyThoseRoutes(self):
        context = {"entries": ENTRIES}

        result = sum_location_route_basket_totals(context, "normal", "Runde 3")

        self.assertEqual(2, result)

    def test_sumLocationRouteBasketTotals_unknownName_countsAsZero(self):
        context = {"entries": ENTRIES}

        result = sum_location_route_basket_totals(
            context, "small", "Runde 3", "Runde 99"
        )

        self.assertEqual(4, result)
