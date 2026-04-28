import datetime

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.services.custom_cycle_delivery_date_calculator import (
    CustomCycleDeliveryDateCalculator,
)
from tapir.deliveries.tests.factories import CustomCycleScheduledDeliveryWeekFactory
from tapir.wirgarten.tests.factories import ProductTypeFactory, GrowingPeriodFactory


class TestDoesProductTypeHaveAtLeastOneDeliveryInTheFuture(TapirUnitTest):
    def test_doesProductTypeHaveAtLeastOneDeliveryInTheFuture_noDeliveriesDefined_returnFalse(
        self,
    ):
        product_type = ProductTypeFactory.build()
        cache = {"scheduled_weeks_by_product_type": {product_type: []}}

        result = CustomCycleDeliveryDateCalculator.does_product_type_have_at_least_one_delivery_in_the_future(
            product_type=product_type,
            reference_date=datetime.date(year=2020, month=5, day=6),
            cache=cache,
        )

        self.assertFalse(result)

    def test_doesProductTypeHaveAtLeastOneDeliveryInTheFuture_onlyPastDeliveriesDefined_returnFalse(
        self,
    ):
        product_type = ProductTypeFactory.build()
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2019, month=1, day=1)
        )
        cache = {
            "scheduled_weeks_by_product_type": {
                product_type: [
                    CustomCycleScheduledDeliveryWeekFactory.build(
                        growing_period=growing_period, product_type=product_type
                    )
                ]
            }
        }

        result = CustomCycleDeliveryDateCalculator.does_product_type_have_at_least_one_delivery_in_the_future(
            product_type=product_type,
            reference_date=datetime.date(year=2020, month=5, day=6),
            cache=cache,
        )

        self.assertFalse(result)

    def test_doesProductTypeHaveAtLeastOneDeliveryInTheFuture_futureDeliveriesExist_returnTrue(
        self,
    ):
        product_type = ProductTypeFactory.build()
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2021, month=1, day=1)
        )
        cache = {
            "scheduled_weeks_by_product_type": {
                product_type: [
                    CustomCycleScheduledDeliveryWeekFactory.build(
                        growing_period=growing_period, product_type=product_type
                    )
                ]
            }
        }

        result = CustomCycleDeliveryDateCalculator.does_product_type_have_at_least_one_delivery_in_the_future(
            product_type=product_type,
            reference_date=datetime.date(year=2020, month=5, day=6),
            cache=cache,
        )

        self.assertTrue(result)
