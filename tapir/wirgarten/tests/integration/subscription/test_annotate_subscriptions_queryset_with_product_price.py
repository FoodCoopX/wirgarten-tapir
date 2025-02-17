import datetime

from django.utils import timezone

from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.subscriptions import (
    annotate_subscriptions_queryset_with_product_price,
)
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAnnotateSubscriptionsQuerysetWithProductPrice(TapirIntegrationTest):
    NOW = timezone.make_aware(datetime.datetime(year=2023, month=6, day=1))
    REFERENCE_DATE = datetime.date(year=2022, month=7, day=16)

    def setUp(self):
        super().setUp()
        ParameterDefinitions().import_definitions()
        mock_timezone(self, self.NOW)

    def test_annotateSubscriptionsQuerysetWithProductPrice_default_returnsCorrectPrice(
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

        subscription = annotate_subscriptions_queryset_with_product_price(
            Subscription.objects.all(), self.REFERENCE_DATE
        ).first()

        self.assertEqual(10, subscription.current_product_price)
