import datetime

from tapir.subscriptions.services.product_type_lowest_free_capacity_after_date_generic import (
    ProductTypeLowestFreeCapacityAfterDateCalculator,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    ProductCapacityFactory,
    SubscriptionFactory,
    ProductPriceFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetLowestCapacityAfterDate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.current_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )
        product_capacity = ProductCapacityFactory.create(
            period=cls.current_period, capacity=10
        )
        cls.product = ProductFactory.create(type=product_capacity.product_type)
        ProductPriceFactory.create(
            product=cls.product,
            size=1,
            valid_from=cls.current_period.start_date,
        )

    def setUp(self) -> None:
        super().setUp()
        self.subscription = SubscriptionFactory.create(
            period=self.current_period,
            product=self.product,
            quantity=1,
        )

    def test_getLowestCapacityAfterDate_singleGrowingPeriod_returnsLowestCapacityInCurrentGrowingPeriod(
        self,
    ):
        result = ProductTypeLowestFreeCapacityAfterDateCalculator.get_lowest_free_capacity_after_date(
            product_type=self.subscription.product.type,
            reference_date=datetime.date(year=2020, month=1, day=1),
            cache={},
        )

        self.assertEqual(9, result)

    def test_getLowestCapacityAfterDate_multipleGrowingPeriods_returnsLowestCapacityOverBothPeriods(
        self,
    ):
        future_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2021, month=1, day=1)
        )
        ProductCapacityFactory.create(
            period=future_period,
            capacity=10,
            product_type=self.subscription.product.type,
        )
        SubscriptionFactory.create(
            period=future_period,
            product=self.subscription.product,
            quantity=2,
        )

        result = ProductTypeLowestFreeCapacityAfterDateCalculator.get_lowest_free_capacity_after_date(
            product_type=self.subscription.product.type,
            reference_date=datetime.date(year=2020, month=1, day=1),
            cache={},
        )

        self.assertEqual(8, result)

    def test_getLowestCapacityAfterDate_productHasNoCapacityInFutureGrowingPeriod_dontConsiderFuturePeriod(
        self,
    ):
        # Regression test for infra#187 https://github.com/FoodCoopX/infra/issues/187
        # If a product type has no capacity defined in a given growing period,
        # that growing period should not be included in the capacity calculations

        future_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2021, month=1, day=1)
        )
        SubscriptionFactory.create(
            period=future_period,
            product=self.subscription.product,
            quantity=2,
        )

        result = ProductTypeLowestFreeCapacityAfterDateCalculator.get_lowest_free_capacity_after_date(
            product_type=self.subscription.product.type,
            reference_date=datetime.date(year=2020, month=1, day=1),
            cache={},
        )

        self.assertEqual(9, result)
