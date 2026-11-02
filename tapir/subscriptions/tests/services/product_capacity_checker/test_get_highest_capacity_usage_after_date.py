import datetime

from tapir.subscriptions.services.product_capacity_checker import (
    ProductCapacityChecker,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    ProductCapacityFactory,
    ProductFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetHighestCapacityUsageAfterDate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )
        product_capacity = ProductCapacityFactory.create(
            period=cls.growing_period, capacity=10
        )
        cls.product = ProductFactory.create(type=product_capacity.product_type)

    def setUp(self) -> None:
        super().setUp()
        SubscriptionFactory.create(
            period=self.growing_period, product=self.product, quantity=1
        )

    def test_getHighestCapacityUsageAfterDate_usageIncreasesLater_returnsLaterUsage(
        self,
    ):
        SubscriptionFactory.create(
            period=self.growing_period,
            product=self.product,
            quantity=2,
            start_date=datetime.date(year=2020, month=6, day=1),
        )

        result = ProductCapacityChecker.get_highest_capacity_usage_after_date(
            product=self.product,
            reference_date=datetime.date(year=2020, month=1, day=1),
            cache={},
        )

        self.assertEqual(3, result)

    def test_getHighestCapacityUsageAfterDate_usageDecreasesLater_returnsUsageAtReferenceDate(
        self,
    ):
        SubscriptionFactory.create(
            period=self.growing_period,
            product=self.product,
            quantity=2,
            end_date=datetime.date(year=2020, month=3, day=31),
        )

        result = ProductCapacityChecker.get_highest_capacity_usage_after_date(
            product=self.product,
            reference_date=datetime.date(year=2020, month=1, day=1),
            cache={},
        )

        self.assertEqual(3, result)

    def test_getHighestCapacityUsageAfterDate_referenceDateAfterLastPossibleCapacityChange_returnsUsageAtReferenceDate(
        self,
    ):
        result = ProductCapacityChecker.get_highest_capacity_usage_after_date(
            product=self.product,
            reference_date=self.growing_period.end_date + datetime.timedelta(weeks=1),
            cache={},
        )

        self.assertEqual(0, result)
