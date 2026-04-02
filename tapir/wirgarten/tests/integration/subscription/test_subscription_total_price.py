import datetime
from decimal import Decimal

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import SubscriptionFactory, ProductPriceFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSubscriptionTotalPrice(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_totalPrice_priceChanges_correctPriceReturned(self):
        # We used to cache the total price of a subscription in the subscription object itself, without checking the date.
        # This meant that when asking the subscription for it's price several times at different dates, the price on the
        # dates after a price change were incorrect.
        subscription = SubscriptionFactory.create(
            quantity=1, start_date=datetime.date(year=2018, month=1, day=1)
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=datetime.date(year=2018, month=1, day=1),
            price=10,
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=datetime.date(year=2018, month=6, day=1),
            price=12,
        )
        price_before = subscription.total_price(
            reference_date=datetime.date(year=2018, month=5, day=1)
        )
        self.assertEqual(Decimal(10), price_before)

        price_after = subscription.total_price(
            reference_date=datetime.date(year=2018, month=6, day=1)
        )
        self.assertEqual(Decimal(12), price_after)
