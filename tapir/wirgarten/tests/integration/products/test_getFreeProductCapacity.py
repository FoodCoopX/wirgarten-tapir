import datetime

from tapir.wirgarten.service.products import get_free_product_capacity
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    ProductTypeFactory,
    ProductCapacityFactory,
    SubscriptionFactory,
    ProductPriceFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak


class TestGetFreeProductCapacity(TapirIntegrationTest):
    def setUp(self):
        set_bypass_keycloak()

    @staticmethod
    def create_growing_period_and_product_price_and_product_capacity():
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2022, month=1, day=1),
            end_date=datetime.date(year=2022, month=12, day=31),
        )

        product_m = ProductFactory.create()
        ProductPriceFactory.create(
            product=product_m,
            price=100,
            valid_from=growing_period.start_date,
        )

        ProductCapacityFactory.create(
            period=growing_period, product_type=product_m.type, capacity=1000
        )

        return growing_period, product_m

    def test_getFreeProductCapacity_noGrowingPeriod_returnsZero(self):
        product_type = ProductTypeFactory.create()

        self.assertEqual(
            0,
            get_free_product_capacity(product_type.id),
        )

    def test_getFreeProductCapacity_noCapacity_returnsZero(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()

        self.assertEqual(
            0,
            get_free_product_capacity(
                product_type.id,
                reference_date=growing_period.start_date + datetime.timedelta(days=60),
            ),
        )

    def test_getFreeProductCapacity_noSubscriptions_returnsFullCapacity(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        ProductCapacityFactory.create(
            period=growing_period, product_type=product_type, capacity=1000
        )

        self.assertEqual(
            1000,
            get_free_product_capacity(
                product_type.id,
                reference_date=growing_period.start_date + datetime.timedelta(days=60),
            ),
        )

    def test_getFreeProductCapacity_hasSubscriptions_returnsCorrectCapacity(self):
        (
            growing_period,
            product_m,
        ) = self.create_growing_period_and_product_price_and_product_capacity()

        product_l = ProductFactory.create(type=product_m.type)
        ProductPriceFactory.create(
            product=product_l,
            price=150,
            valid_from=growing_period.start_date,
        )

        SubscriptionFactory.create(period=growing_period, quantity=2, product=product_m)
        SubscriptionFactory.create(period=growing_period, quantity=1, product=product_l)

        self.assertEqual(
            650,
            get_free_product_capacity(
                product_m.type.id,
                reference_date=datetime.date(year=2022, month=4, day=1),
            ),
        )

    def test_getFreeProductCapacity_hasSubscriptionsInTrial_returnsCorrectCapacity(
        self,
    ):
        (
            growing_period,
            product_m,
        ) = self.create_growing_period_and_product_price_and_product_capacity()

        SubscriptionFactory.create(
            period=growing_period,
            quantity=1,
            product=product_m,
            start_date=datetime.date(year=2022, month=3, day=1),
        )

        self.assertEqual(
            900,
            get_free_product_capacity(
                product_m.type.id,
                reference_date=datetime.date(year=2022, month=3, day=15),
            ),
        )

    def test_getFreeProductCapacity_hasEndedSubscription_endedSubscriptionNotTakenIntoAccount(
        self,
    ):
        (
            growing_period,
            product_m,
        ) = self.create_growing_period_and_product_price_and_product_capacity()
        SubscriptionFactory.create(
            period=growing_period,
            quantity=1,
            product=product_m,
            end_date=datetime.date(year=2022, month=3, day=1),
        )

        self.assertEqual(
            1000,
            get_free_product_capacity(
                product_m.type.id,
                reference_date=datetime.date(year=2022, month=3, day=15),
            ),
        )

    def test_getFreeProductCapacity_hasSubscriptionCloseToEndButStillValid_subscriptionIsTakenIntoAccount(
        self,
    ):
        (
            growing_period,
            product_m,
        ) = self.create_growing_period_and_product_price_and_product_capacity()
        SubscriptionFactory.create(
            period=growing_period,
            quantity=1,
            product=product_m,
            end_date=datetime.date(year=2022, month=4, day=30),
        )

        self.assertEqual(
            900,
            get_free_product_capacity(
                product_m.type.id,
                reference_date=datetime.date(year=2022, month=4, day=15),
            ),
        )
