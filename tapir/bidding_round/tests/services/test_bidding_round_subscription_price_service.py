import datetime
from decimal import Decimal

from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.services.bidding_round_subscription_price_service import (
    BiddingRoundSubscriptionPriceService,
)
from tapir.bidding_round.tests.factories import BiddingRoundFactory
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import ProductPriceFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundSubscriptionPriceService(TapirIntegrationTest):
    REFERENCE_DATE = datetime.date(year=2022, month=7, day=16)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _create_subscription_with_link(
        self, price_mode, monthly_price_per_share, quantity=3
    ):
        subscription = SubscriptionFactory.create(
            quantity=quantity, price_mode=price_mode
        )
        bidding_round = BiddingRoundFactory.create(growing_period=subscription.period)
        BiddingRoundCreatedSubscription.objects.create(
            round=bidding_round,
            subscription=subscription,
            monthly_price_per_share=monthly_price_per_share,
        )
        return subscription

    def test_getPriceForSubscription_biddingRoundBid_returnsTheFrozenPrice(self):
        subscription = self._create_subscription_with_link(
            price_mode=Subscription.PriceMode.BIDDING_ROUND_BID,
            monthly_price_per_share=Decimal("5.0000"),
        )

        self.assertEqual(
            Decimal("15.0000"),
            BiddingRoundSubscriptionPriceService.get_price_for_subscription(
                subscription, cache={}
            ),
        )

    def test_getPriceForSubscription_autoRenewed_returnsTheFrozenPrice(self):
        subscription = self._create_subscription_with_link(
            price_mode=Subscription.PriceMode.BIDDING_ROUND_AUTO_RENEWED,
            monthly_price_per_share=Decimal("5.0000"),
        )

        self.assertEqual(
            Decimal("15.0000"),
            BiddingRoundSubscriptionPriceService.get_price_for_subscription(
                subscription, cache={}
            ),
        )

    def test_getPriceForSubscription_priceOverridden_returnsTheOverride(self):
        subscription = self._create_subscription_with_link(
            price_mode=Subscription.PriceMode.BIDDING_ROUND_BID,
            monthly_price_per_share=Decimal("5.0000"),
        )
        subscription.price_override = Decimal("0")

        self.assertEqual(
            Decimal("0"),
            BiddingRoundSubscriptionPriceService.get_price_for_subscription(
                subscription, cache={}
            ),
        )

    def test_getPriceForSubscription_standardMode_returnsNone(self):
        subscription = SubscriptionFactory.create()

        self.assertIsNone(
            BiddingRoundSubscriptionPriceService.get_price_for_subscription(
                subscription, cache={}
            )
        )

    def test_annotatePricePerShare_biddingRoundBid_usesTheFrozenPriceInTheQueryset(
        self,
    ):
        subscription = self._create_subscription_with_link(
            price_mode=Subscription.PriceMode.BIDDING_ROUND_BID,
            monthly_price_per_share=Decimal("5.0000"),
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=self.REFERENCE_DATE - datetime.timedelta(days=10),
            price=10,
        )

        annotated = SubscriptionPriceCalculator.annotate_subscriptions_queryset_with_monthly_price(
            queryset=Subscription.objects.all(), reference_date=self.REFERENCE_DATE
        ).first()

        self.assertEqual(Decimal("15.0000"), annotated.monthly_price)
