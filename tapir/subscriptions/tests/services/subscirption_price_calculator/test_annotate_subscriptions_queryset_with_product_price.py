import datetime

from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import SubscriptionFactory, ProductPriceFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAnnotateSubscriptionsQuerysetWithProductPrice(TapirIntegrationTest):
    REFERENCE_DATE = datetime.date(year=2022, month=7, day=16)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_annotateSubscriptionsQuerysetWithProductPrice_default_annotatesCorrectPrice(
        self,
    ):
        subscription_1 = SubscriptionFactory.create(quantity=3)
        ProductPriceFactory.create(
            product=subscription_1.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=20),
            price=20,
        )
        ProductPriceFactory.create(
            product=subscription_1.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=10,
        )
        ProductPriceFactory.create(
            product=subscription_1.product,
            valid_from=self.REFERENCE_DATE + datetime.timedelta(days=15),
            price=15,
        )

        # Adding other subscriptions and prices to make sure they don't contaminate the target subscription
        SubscriptionFactory.create(product=subscription_1.product)
        subscription_2 = SubscriptionFactory.create()
        ProductPriceFactory.create(
            product=subscription_2.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=15,
        )

        subscription_1 = SubscriptionPriceCalculator.annotate_subscriptions_queryset_with_product_price(
            queryset=Subscription.objects.all(), reference_date=self.REFERENCE_DATE
        ).get(
            id=subscription_1.id
        )

        self.assertEqual(10, subscription_1.current_product_price)
