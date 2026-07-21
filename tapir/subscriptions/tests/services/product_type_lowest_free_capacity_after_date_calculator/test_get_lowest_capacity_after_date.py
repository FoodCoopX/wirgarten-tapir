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
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetLowestCapacityAfterDate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        current_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )
        product_capacity = ProductCapacityFactory.create(
            period=current_period, capacity=10
        )
        cls.subscription = SubscriptionFactory.create(
            period=current_period,
            product__type=product_capacity.product_type,
            quantity=1,
        )
        ProductPriceFactory.create(
            product=cls.subscription.product,
            size=1,
            valid_from=current_period.start_date,
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
