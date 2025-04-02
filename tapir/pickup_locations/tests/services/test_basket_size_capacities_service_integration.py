from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import (
    ProductBasketSizeEquivalence,
    PickupLocationBasketCapacity,
)
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import ProductFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBasketSizeCapacitiesServiceIntegration(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_BASKET_SIZES).update(
            value="small;medium"
        )

    def test_getBasketSizesEquivalencesForProduct_productHasNoSavedEquivalences_returnsZeroAsDefault(
        self,
    ):
        product = ProductFactory.create()
        result = BasketSizeCapacitiesService.get_basket_size_equivalences_for_product(
            product
        )

        self.assertEqual({"small": 0, "medium": 0}, result)

    def test_getBasketSizesEquivalencesForProduct_productHasSavedEquivalences_returnsCorrectValue(
        self,
    ):
        product = ProductFactory.create()
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="small", product=product, quantity=12
        )

        result = BasketSizeCapacitiesService.get_basket_size_equivalences_for_product(
            product
        )

        self.assertEqual({"small": 12, "medium": 0}, result)

    def test_getBasketSizesEquivalencesForProduct_productHasEquivalencesForNonExistingSizes_extraEquivalencesNotIncludedInResult(
        self,
    ):
        product = ProductFactory.create()
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="small", product=product, quantity=12
        )
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="large", product=product, quantity=3
        )

        result = BasketSizeCapacitiesService.get_basket_size_equivalences_for_product(
            product
        )

        self.assertEqual({"small": 12, "medium": 0}, result)

    def test_getBasketSizeCapacitiesForPickupLocation_pickupLocationHasNoSavedCapacity_returnsNoneAsDefault(
        self,
    ):
        pickup_location = PickupLocationFactory.create()

        result = (
            BasketSizeCapacitiesService.get_basket_size_capacities_for_pickup_location(
                pickup_location
            )
        )

        self.assertEqual({"small": None, "medium": None}, result)

    def test_getBasketSizeCapacitiesForPickupLocation_pickupLocationHasSavedCapacity_returnsCorrectValue(
        self,
    ):
        pickup_location = PickupLocationFactory.create()
        PickupLocationBasketCapacity.objects.create(
            pickup_location=pickup_location, basket_size_name="medium", capacity=13
        )

        result = (
            BasketSizeCapacitiesService.get_basket_size_capacities_for_pickup_location(
                pickup_location
            )
        )

        self.assertEqual({"small": None, "medium": 13}, result)

    def test_getBasketSizeCapacitiesForPickupLocation_pickupLocationHasCapacityForNonExistingSize_extraCapacityNotIncludedInResult(
        self,
    ):
        pickup_location = PickupLocationFactory.create()
        PickupLocationBasketCapacity.objects.create(
            pickup_location=pickup_location, basket_size_name="medium", capacity=13
        )
        PickupLocationBasketCapacity.objects.create(
            pickup_location=pickup_location, basket_size_name="large", capacity=15
        )

        result = (
            BasketSizeCapacitiesService.get_basket_size_capacities_for_pickup_location(
                pickup_location
            )
        )

        self.assertEqual({"small": None, "medium": 13}, result)
