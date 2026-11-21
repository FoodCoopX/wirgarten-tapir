import datetime
from decimal import Decimal
from unittest.mock import patch, Mock, MagicMock

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.deliveries.services.monthly_delivery_date_counter import (
    MonthlyDeliveryDateCounter,
)
from tapir.deliveries.services.partial_month_calculation_mode_decider import (
    PartialMonthCalculationModeDecider,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, CUSTOM_CYCLE, EVERY_FOUR_WEEKS
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    PartialMonthCalculationModeDecider,
    "is_proportional_mode_active",
    autospec=True,
    return_value=False,
)
@patch.object(
    DeliveryPriceCalculator,
    "get_price_of_single_delivery_for_subscription",
    autospec=True,
)
@patch("tapir.deliveries.services.joker_value_service.get_product_price", autospec=True)
class TestGetSubscriptionPart(TapirUnitTest):
    # 2021 has 52 weeks
    JOKER_DATE = datetime.date(year=2021, month=5, day=7)
    OCTOBER_DELIVERY_DATE = datetime.date(year=2026, month=10, day=8)

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
        _: Mock,
    ):
        self.setup_prices(
            mock_get_product_price=mock_get_product_price,
            mock_get_price_of_single_delivery=mock_get_price_of_single_delivery,
            delivery_value=Decimal("2.3"),
        )
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0], quantity=1)
        cache = {}

        part = JokerValueService._get_subscription_part(
            subscription=subscription, delivery_date=self.JOKER_DATE, cache=cache
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
        _: Mock,
    ):
        self.setup_prices(
            mock_get_product_price=mock_get_product_price,
            mock_get_price_of_single_delivery=mock_get_price_of_single_delivery,
            delivery_value=Decimal("13.8"),
        )
        subscription = self.build_subscription(delivery_cycle=EVEN_WEEKS[0], quantity=3)

        part = JokerValueService._get_subscription_part(
            subscription=subscription, delivery_date=self.JOKER_DATE, cache={}
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
        _: Mock,
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
            subscription=subscription, delivery_date=self.JOKER_DATE, cache={}
        )

        self.assertEqual(Decimal(10), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M: Preis pro Lieferung 10,00 €", part.explanation
        )

    def test_getSubscriptionPart_customCycleWithQuantity_explainsQuantity(
        self,
        mock_get_product_price: Mock,
        mock_get_price_of_single_delivery: Mock,
        _: Mock,
    ):
        self.setup_prices(
            mock_get_product_price=mock_get_product_price,
            mock_get_price_of_single_delivery=mock_get_price_of_single_delivery,
            delivery_value=Decimal(30),
        )
        subscription = self.build_subscription(
            delivery_cycle=CUSTOM_CYCLE[0], quantity=3
        )

        part = JokerValueService._get_subscription_part(
            subscription=subscription, delivery_date=self.JOKER_DATE, cache={}
        )

        self.assertEqual(Decimal(30), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M: Preis pro Lieferung 10,00 € × 3 Anteile = 30,00 €",
            part.explanation,
        )

    def test_getSubscriptionPart_customCycleWithPriceOverride_explainsOverridePrice(
        self,
        mock_get_product_price: MagicMock,
        mock_get_price_of_single_delivery: MagicMock,
        _: MagicMock,
    ):
        mock_get_price_of_single_delivery.return_value = Decimal(15)
        subscription = self.build_subscription(
            delivery_cycle=CUSTOM_CYCLE[0], quantity=2
        )
        subscription.price_override = Decimal(15)

        part = JokerValueService._get_subscription_part(
            subscription=subscription, delivery_date=self.JOKER_DATE, cache={}
        )

        self.assertEqual(Decimal(15), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M (Sonderpreis): Preis pro Lieferung 15,00 €",
            part.explanation,
        )
        mock_get_product_price.assert_not_called()

    def test_getSubscriptionPart_priceOverride_explainsOverridePrice(
        self,
        mock_get_product_price: MagicMock,
        mock_get_price_of_single_delivery: MagicMock,
        _: MagicMock,
    ):
        mock_get_price_of_single_delivery.return_value = Decimal("6.92")
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0], quantity=2)
        subscription.price_override = Decimal(30)

        part = JokerValueService._get_subscription_part(
            subscription=subscription, delivery_date=self.JOKER_DATE, cache={}
        )

        self.assertEqual(Decimal("6.92"), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M (Sonderpreis): 30,00 € monatlich × 12 ÷ 52 Wochen = 6,92 €",
            part.explanation,
        )
        mock_get_product_price.assert_not_called()

    @patch.object(
        MonthlyDeliveryDateCounter,
        "count_delivery_dates_in_month",
        autospec=True,
        return_value=5,
    )
    @patch.object(
        SubscriptionPriceCalculator,
        "get_monthly_price",
        autospec=True,
        return_value=Decimal(95),
    )
    def test_getSubscriptionPart_proportionalModeMonthWithFiveDates_returnsMonthlyPriceDividedByDates(
        self,
        mock_get_monthly_price: MagicMock,
        mock_count_delivery_dates_in_month: MagicMock,
        _: MagicMock,
        mock_get_price_of_single_delivery: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        mock_is_proportional_mode_active.return_value = True
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0], quantity=1)
        cache = {}

        part = JokerValueService._get_subscription_part(
            subscription=subscription,
            delivery_date=self.OCTOBER_DELIVERY_DATE,
            cache=cache,
        )

        self.assertEqual(Decimal(19), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M: 95,00 € monatlich ÷ 5 Liefertermine im Oktober = 19,00 €",
            part.explanation,
        )
        mock_is_proportional_mode_active.assert_called_once_with(
            first_of_month=datetime.date(year=2026, month=10, day=1), cache=cache
        )
        mock_get_monthly_price.assert_called_once_with(
            subscription=subscription,
            reference_date=self.OCTOBER_DELIVERY_DATE,
            cache=cache,
        )
        mock_count_delivery_dates_in_month.assert_called_once_with(
            member_id=subscription.member_id,
            product_type=subscription.product.type,
            first_of_month=datetime.date(year=2026, month=10, day=1),
            contract_start=None,
            contract_end=None,
            cache=cache,
        )
        mock_get_price_of_single_delivery.assert_not_called()

    @patch.object(
        MonthlyDeliveryDateCounter, "count_delivery_dates_in_month", autospec=True
    )
    @patch.object(
        SubscriptionPriceCalculator,
        "get_monthly_price",
        autospec=True,
        return_value=Decimal(95),
    )
    def test_getSubscriptionPart_proportionalModeAllCycles_returnsMonthlyPriceDividedByDates(
        self,
        _: MagicMock,
        mock_count_delivery_dates_in_month: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        mock_is_proportional_mode_active.return_value = True
        for delivery_cycle, number_of_dates, expected in [
            (WEEKLY[0], 4, Decimal("23.75")),
            (EVEN_WEEKS[0], 2, Decimal("47.50")),
            (EVERY_FOUR_WEEKS[0], 1, Decimal(95)),
        ]:
            with self.subTest(delivery_cycle=delivery_cycle):
                mock_count_delivery_dates_in_month.return_value = number_of_dates
                subscription = self.build_subscription(
                    delivery_cycle=delivery_cycle, quantity=1
                )

                part = JokerValueService._get_subscription_part(
                    subscription=subscription,
                    delivery_date=datetime.date(year=2026, month=11, day=5),
                    cache={},
                )

                self.assertEqual(expected, part.value)

    @patch.object(
        MonthlyDeliveryDateCounter,
        "count_delivery_dates_in_month",
        autospec=True,
        return_value=5,
    )
    @patch.object(
        SubscriptionPriceCalculator,
        "get_monthly_price",
        autospec=True,
        return_value=Decimal(190),
    )
    def test_getSubscriptionPart_proportionalModeSeveralShares_quantityShownInName(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        ____: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        mock_is_proportional_mode_active.return_value = True
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0], quantity=2)

        part = JokerValueService._get_subscription_part(
            subscription=subscription,
            delivery_date=self.OCTOBER_DELIVERY_DATE,
            cache={},
        )

        self.assertEqual(Decimal(38), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M (2 Anteile): 190,00 € monatlich ÷ 5 Liefertermine im Oktober = 38,00 €",
            part.explanation,
        )

    @patch.object(
        MonthlyDeliveryDateCounter,
        "count_delivery_dates_in_month",
        autospec=True,
        return_value=5,
    )
    @patch.object(
        SubscriptionPriceCalculator,
        "get_monthly_price",
        autospec=True,
        return_value=Decimal(80),
    )
    def test_getSubscriptionPart_proportionalModePriceOverride_overrideShownInName(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        ____: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        mock_is_proportional_mode_active.return_value = True
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0], quantity=2)
        subscription.price_override = Decimal(80)

        part = JokerValueService._get_subscription_part(
            subscription=subscription,
            delivery_date=self.OCTOBER_DELIVERY_DATE,
            cache={},
        )

        self.assertEqual(Decimal(16), part.value)
        self.assertEqual(
            "Ernteanteil Gemüse M (Sonderpreis): 80,00 € monatlich ÷ 5 Liefertermine im Oktober = 16,00 €",
            part.explanation,
        )

    @patch.object(
        MonthlyDeliveryDateCounter,
        "count_delivery_dates_in_month",
        autospec=True,
        return_value=0,
    )
    @patch.object(
        SubscriptionPriceCalculator,
        "get_monthly_price",
        autospec=True,
        return_value=Decimal(95),
    )
    def test_getSubscriptionPart_proportionalModeNoDeliveryDateInMonth_returnsZero(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        ____: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        mock_is_proportional_mode_active.return_value = True
        subscription = self.build_subscription(delivery_cycle=WEEKLY[0], quantity=1)

        part = JokerValueService._get_subscription_part(
            subscription=subscription,
            delivery_date=self.OCTOBER_DELIVERY_DATE,
            cache={},
        )

        self.assertEqual(Decimal(0), part.value)

    def test_getSubscriptionPart_customCycle_decidesWithoutProportionalMode(
        self,
        mock_get_product_price: MagicMock,
        mock_get_price_of_single_delivery: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        mock_is_proportional_mode_active.return_value = True
        self.setup_prices(
            mock_get_product_price=mock_get_product_price,
            mock_get_price_of_single_delivery=mock_get_price_of_single_delivery,
            delivery_value=Decimal(10),
        )
        subscription = self.build_subscription(
            delivery_cycle=CUSTOM_CYCLE[0], quantity=1
        )

        part = JokerValueService._get_subscription_part(
            subscription=subscription,
            delivery_date=self.OCTOBER_DELIVERY_DATE,
            cache={},
        )

        self.assertEqual(Decimal(10), part.value)
        mock_is_proportional_mode_active.assert_not_called()
