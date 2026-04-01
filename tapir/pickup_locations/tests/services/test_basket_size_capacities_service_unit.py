from django.test import SimpleTestCase

from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)


class TestBasketSizeCapacitiesServiceUnit(SimpleTestCase):
    def test_validateBasketSizes_emptyString_noException(self):
        BasketSizeCapacitiesService.validate_basket_sizes("")

    def test_validateBasketSizes_sizesEndingWithSemicolon_noException(self):
        BasketSizeCapacitiesService.validate_basket_sizes("small;medium;")

    def test_validateBasketSizes_sizesNotEndingWithSemicolon_noException(self):
        BasketSizeCapacitiesService.validate_basket_sizes("small;medium")

    def test_getBasketSizes_emptyString_returnsEmptyArray(self):
        self.assertEqual([], BasketSizeCapacitiesService.get_basket_sizes(""))

    def test_getBasketSizes_givenListContainsEmptyEntries_returnsOnlyNonEmptyEntries(
        self,
    ):
        self.assertEqual(
            ["small", "medium"],
            BasketSizeCapacitiesService.get_basket_sizes("small;;medium;"),
        )

    def test_getBasketSizes_default_returnsCorrectList(self):
        self.assertEqual(
            ["small", "medium"],
            BasketSizeCapacitiesService.get_basket_sizes("small;medium"),
        )
