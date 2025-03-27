import datetime

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    PickupLocationFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetCurrentCapacityUsage(TapirIntegrationTest):
    def setUp(self) -> None:
        self.NOW = mock_timezone(self, factories.NOW)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=Parameter.PICKING_BASKET_SIZES).update(
            value="small;medium"
        )
        cls.product_s = ProductFactory(name="S")
        cls.product_m = ProductFactory(name="M")
        cls.product_l = ProductFactory(name="L")
        ProductBasketSizeEquivalence.objects.bulk_create(
            [
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=cls.product_s, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=cls.product_s, quantity=0
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=cls.product_m, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=cls.product_l, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=cls.product_l, quantity=1
                ),
            ]
        )
        cls.pickup_location_a = PickupLocationFactory.create()
        cls.pickup_location_b = PickupLocationFactory.create()

    def test_getCurrentCapacityUsage_memberNotAtPickupStation_subscriptionNotAddedToUsage(
        self,
    ):
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member, pickup_location=self.pickup_location_a
        )
        SubscriptionFactory.create(member=member, product=self.product_s)

        result = PickupLocationCapacityModeBasketChecker.get_current_capacity_usage(
            self.pickup_location_b, "small", self.NOW.date()
        )

        self.assertEqual(0, result)

    def test_getCurrentCapacityUsage_subscriptionNotActive_subscriptionNotAddedToUsage(
        self,
    ):
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member, pickup_location=self.pickup_location_a
        )
        SubscriptionFactory.create(member=member, product=self.product_s)

        result = PickupLocationCapacityModeBasketChecker.get_current_capacity_usage(
            self.pickup_location_a,
            "small",
            self.NOW.date() + datetime.timedelta(days=365),
        )

        self.assertEqual(0, result)

    def test_getCurrentCapacityUsage_default_countsCorrectly(self):
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member, pickup_location=self.pickup_location_a
        )
        SubscriptionFactory.create(member=member, product=self.product_s, quantity=3)
        SubscriptionFactory.create(member=member, product=self.product_m, quantity=2)

        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member, pickup_location=self.pickup_location_a
        )
        SubscriptionFactory.create(member=member, product=self.product_l, quantity=1)

        self.assertEqual(
            4,
            PickupLocationCapacityModeBasketChecker.get_current_capacity_usage(
                self.pickup_location_a,
                "small",
                self.NOW.date(),
            ),
        )
        self.assertEqual(
            3,
            PickupLocationCapacityModeBasketChecker.get_current_capacity_usage(
                self.pickup_location_a,
                "medium",
                self.NOW.date(),
            ),
        )
