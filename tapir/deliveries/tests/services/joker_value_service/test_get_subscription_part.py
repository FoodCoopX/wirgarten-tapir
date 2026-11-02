import datetime
from decimal import Decimal
from unittest.mock import patch, Mock

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, CUSTOM_CYCLE
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    DeliveryPriceCalculator,
    "get_price_of_single_delivery_for_subscription",
    autospec=True,
)
@patch("tapir.deliveries.services.joker_value_service.get_product_price", autospec=True)
class TestGetSubscriptionPart(TapirUnitTest):
    # 2021 has 52 weeks
    JOKER_DATE = datetime.date(year=2021, month=5, day=7)

    def build_subscription(self, delivery_cycle: str, quantity: int):
        product = ProductFactory.build(
            name="Gemüse M",
            type__name="Ernteanteil",
            type__delivery_cycle=delivery_cycle,
        )
        return SubscriptionFactory.build(product=product, quantity=quantity)

    def setup_prices(
        self,
        mock_get_product_price: Mock,
        mock_get_price_of_single_delivery: Mock,
        delivery_value: Decimal,
    ):
        mock_get_product_price.return_value = ProductPriceFactory.build(
            price=Decimal(10)
        )
        mock_get_price_of_single_delivery.return_value = delivery_value

    def test_getSubscriptionPart_singleShare_noQuantityInExplanation(
        self,
        mock_get_product_price: Mock,
        mock_get_price_of_single_delivery: Mock,
    ):
        self.setup_prices(
            mock_get_product_price=mock_get_product_price,
            mock_get_price_of_single_delivery=mock_get_price_of_single_delivery,
            delivery_value=Decimal("2.3"),
        )
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0], quantity=1)
        cache = {}

        part = JokerValueService._get_subscription_part(
            subscription=subscription, joker_date=self.JOKER_DATE, cache=cache
        )

        self.assertEqual(Decimal("2.3"), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M: 10,00 € monatlich × 12 ÷ 52 Wochen = 2,30 €",
            part.explanation,
        )
        mock_get_product_price.assert_called_once_with(
            product=subscription.product, reference_date=self.JOKER_DATE, cache=cache
        )
        mock_get_price_of_single_delivery.assert_called_once_with(
            subscription=subscription, at_date=self.JOKER_DATE, cache=cache
        )

    def test_getSubscriptionPart_severalShares_quantityInExplanation(
        self,
        mock_get_product_price: Mock,
        mock_get_price_of_single_delivery: Mock,
    ):
        self.setup_prices(
            mock_get_product_price=mock_get_product_price,
            mock_get_price_of_single_delivery=mock_get_price_of_single_delivery,
            delivery_value=Decimal("13.8"),
        )
        subscription = self.build_subscription(delivery_cycle=EVEN_WEEKS[0], quantity=3)

        part = JokerValueService._get_subscription_part(
            subscription=subscription, joker_date=self.JOKER_DATE, cache={}
        )

        self.assertEqual(Decimal("13.8"), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M: 10,00 € monatlich × 12 ÷ 52 Wochen × 2 (Lieferung alle 2 Wochen) × 3 Anteile = 13,80 €",
            part.explanation,
        )

    def test_getSubscriptionPart_customCycle_explainsPricePerDelivery(
        self,
        mock_get_product_price: Mock,
        mock_get_price_of_single_delivery: Mock,
    ):
        self.setup_prices(
            mock_get_product_price=mock_get_product_price,
            mock_get_price_of_single_delivery=mock_get_price_of_single_delivery,
            delivery_value=Decimal(10),
        )
        subscription = self.build_subscription(
            delivery_cycle=CUSTOM_CYCLE[0], quantity=1
        )

        part = JokerValueService._get_subscription_part(
            subscription=subscription, joker_date=self.JOKER_DATE, cache={}
        )

        self.assertEqual(Decimal(10), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M: Preis pro Lieferung 10,00 €", part.explanation
        )
