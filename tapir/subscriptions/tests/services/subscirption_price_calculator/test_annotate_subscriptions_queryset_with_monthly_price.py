import datetime
from decimal import Decimal

from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import SubscriptionFactory, ProductPriceFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAnnotateSubscriptionsQuerysetWithMonthlyPrice(TapirIntegrationTest):
    REFERENCE_DATE = datetime.date(year=2022, month=7, day=16)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_annotateSubscriptionsQuerysetWithMonthlyPrice_default_annotatesCorrectPrice(
        self,
    ):
        subscription = SubscriptionFactory.create(quantity=3)
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=10,
        )

        subscription = SubscriptionPriceCalculator.annotate_subscriptions_queryset_with_monthly_price(
            queryset=Subscription.objects.all(), reference_date=self.REFERENCE_DATE
        ).first()

        self.assertEqual(Decimal(30), subscription.monthly_price)

    def test_annotateSubscriptionsQuerysetWithMonthlyPrice_priceOverridden_annotatesOverriddenPrice(
        self,
    ):
        subscription = SubscriptionFactory.create(quantity=3, price_override=12.75)
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=10,
        )

        subscription = SubscriptionPriceCalculator.annotate_subscriptions_queryset_with_monthly_price(
            queryset=Subscription.objects.all(), reference_date=self.REFERENCE_DATE
        ).first()

        self.assertEqual(Decimal(12.75), subscription.monthly_price)
