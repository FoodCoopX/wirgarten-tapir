import datetime

from django.utils import timezone

from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.subscriptions import (
    annotate_subscriptions_queryset_with_product_price,
    annotate_subscriptions_queryset_with_monthly_payment_without_solidarity,
    annotate_subscriptions_queryset_with_monthly_payment_including_solidarity,
)
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestSubscriptionAnnotations(TapirIntegrationTest):
    NOW = timezone.make_aware(datetime.datetime(year=2023, month=6, day=1))
    REFERENCE_DATE = datetime.date(year=2022, month=7, day=16)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, self.NOW)

    def test_annotateSubscriptionsQuerysetWithProductPrice_default_annotatesCorrectPrice(
        self,
    ):
        subscription = SubscriptionFactory.create(quantity=3)
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=20),
            price=20,
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=10,
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE + datetime.timedelta(days=15),
            price=15,
        )

        # Adding other subscriptions and prices to make sure they don't contaminate the target subscription
        SubscriptionFactory.create(product=subscription.product)
        subscription_2 = SubscriptionFactory.create()
        ProductPriceFactory.create(
            product=subscription_2.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=15,
        )

        subscription = annotate_subscriptions_queryset_with_product_price(
            Subscription.objects.all(), self.REFERENCE_DATE
        ).get(id=subscription.id)

        self.assertEqual(10, subscription.current_product_price)

    def test_annotateSubscriptionsQuerysetWithMonthlyPaymentWithoutSolidarity_default_annotatesCorrectPrice(
        self,
    ):
        subscription = SubscriptionFactory.create(quantity=3)
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=10,
        )

        subscription = (
            annotate_subscriptions_queryset_with_monthly_payment_without_solidarity(
                Subscription.objects.all(), self.REFERENCE_DATE
            ).first()
        )

        self.assertEqual(30, subscription.monthly_price_without_solidarity)

    def test_annotateSubscriptionsQuerysetWithMonthlyPaymentIncludingSolidarity_noSolidarity_annotatesCorrectPrice(
        self,
    ):
        subscription = SubscriptionFactory.create(
            quantity=3, solidarity_price_percentage=0
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=10,
        )

        subscription = (
            annotate_subscriptions_queryset_with_monthly_payment_including_solidarity(
                Subscription.objects.all(), self.REFERENCE_DATE
            ).first()
        )

        self.assertEqual(30, subscription.monthly_payment)

    def test_annotateSubscriptionsQuerysetWithMonthlyPaymentIncludingSolidarity_hasSolidarityFactor_annotatesCorrectPrice(
        self,
    ):
        subscription = SubscriptionFactory.create(
            quantity=3, solidarity_price_percentage=0.1
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=10,
        )

        subscription = (
            annotate_subscriptions_queryset_with_monthly_payment_including_solidarity(
                Subscription.objects.all(), self.REFERENCE_DATE
            ).first()
        )

        self.assertEqual(33, subscription.monthly_payment)

    def test_annotateSubscriptionsQuerysetWithMonthlyPaymentIncludingSolidarity_hasAbsoluteSolidarity_annotatesCorrectPrice(
        self,
    ):
        subscription = SubscriptionFactory.create(
            quantity=3, solidarity_price_absolute=15
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=10,
        )

        subscription = (
            annotate_subscriptions_queryset_with_monthly_payment_including_solidarity(
                Subscription.objects.all(), self.REFERENCE_DATE
            ).first()
        )

        self.assertEqual(45, subscription.monthly_payment)
