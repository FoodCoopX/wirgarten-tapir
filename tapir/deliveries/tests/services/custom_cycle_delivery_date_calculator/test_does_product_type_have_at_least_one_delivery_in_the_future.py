import datetime

from django.test import SimpleTestCase

from tapir.deliveries.services.custom_cycle_delivery_date_calculator import (
    CustomCycleDeliveryDateCalculator,
)
from tapir.deliveries.tests.factories import CustomCycleDeliveryWeeksFactory
from tapir.wirgarten.tests.factories import ProductTypeFactory, GrowingPeriodFactory


class TestDoesProductTypeHaveAtLeastOneDeliveryInTheFuture(SimpleTestCase):
    def test_doesProductTypeHaveAtLeastOneDeliveryInTheFuture_noDeliveriesDefined_returnFalse(
        self,
    ):
        product_type = ProductTypeFactory.build()
        cache = {"delivery_week_objects_by_product_type": {product_type: []}}

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
            "delivery_week_objects_by_product_type": {
                product_type: [
                    CustomCycleDeliveryWeeksFactory.build(
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
            "delivery_week_objects_by_product_type": {
                product_type: [
                    CustomCycleDeliveryWeeksFactory.build(
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
