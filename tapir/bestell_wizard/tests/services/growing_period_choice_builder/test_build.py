import datetime

from tapir.bestell_wizard.services.growing_period_choice_builder import (
    GrowingPeriodChoiceBuilder,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductPriceFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestBuild(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, now=datetime.datetime(year=2026, month=6, day=1))
        self.current_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        self.next_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        self.product = ProductFactory.create(capacity=10)
        for period in [self.current_period, self.next_period]:
            ProductCapacityFactory.create(
                product_type=self.product.type, period=period, capacity=10
            )
        ProductPriceFactory.create(
            product=self.product, size=1, valid_from=self.current_period.start_date
        )
        SubscriptionFactory.create(
            period=self.current_period, product=self.product, quantity=10
        )

    def test_build_firstPeriodFull_onlyFirstPeriodListsTheProductAsAtCapacity(
        self,
    ):
        current_choice = GrowingPeriodChoiceBuilder.build(
            growing_period=self.current_period, cache={}
        )
        next_choice = GrowingPeriodChoiceBuilder.build(
            growing_period=self.next_period, cache={}
        )

        self.assertEqual(
            [self.product.id], current_choice.product_ids_that_are_already_at_capacity
        )
        self.assertEqual(
            [self.product.type.id],
            current_choice.product_type_ids_that_are_already_at_capacity,
        )
        self.assertEqual([], next_choice.product_ids_that_are_already_at_capacity)
        self.assertEqual([], next_choice.product_type_ids_that_are_already_at_capacity)

    def test_build_pickupLocationStartsInNextPeriod_onlyListedInNextPeriod(self):
        pickup_location = PickupLocationFactory.create(
            start_date=self.next_period.start_date
        )

        current_choice = GrowingPeriodChoiceBuilder.build(
            growing_period=self.current_period, cache={}
        )
        next_choice = GrowingPeriodChoiceBuilder.build(
            growing_period=self.next_period, cache={}
        )

        self.assertEqual([], current_choice.pickup_locations)
        self.assertEqual([pickup_location], next_choice.pickup_locations)

    def test_build_productTypeWithoutCapacityInPeriod_notIncluded(self):
        product_type_only_next_period = ProductTypeFactory.create()
        ProductCapacityFactory.create(
            product_type=product_type_only_next_period, period=self.next_period
        )

        current_choice = GrowingPeriodChoiceBuilder.build(
            growing_period=self.current_period, cache={}
        )
        next_choice = GrowingPeriodChoiceBuilder.build(
            growing_period=self.next_period, cache={}
        )

        self.assertEqual([self.product.type], current_choice.product_types)
        self.assertCountEqual(
            [self.product.type, product_type_only_next_period],
            next_choice.product_types,
        )

    def test_build_default_contractStartDateIsFirstContractStartInThePeriod(self):
        next_choice = GrowingPeriodChoiceBuilder.build(
            growing_period=self.next_period, cache={}
        )

        self.assertEqual(
            datetime.date(year=2027, month=1, day=4), next_choice.contract_start_date
        )
