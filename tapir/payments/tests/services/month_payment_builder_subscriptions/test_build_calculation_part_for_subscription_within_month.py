import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from tapir.deliveries.services.monthly_delivery_date_counter import (
    MonthlyDeliveryDateCounter,
)
from tapir.deliveries.services.partial_month_calculation_mode_decider import (
    PartialMonthCalculationModeDecider,
)
from tapir.utils.dataclasses import CalculationPart
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.wirgarten.constants import (
    WEEKLY,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
    CUSTOM_CYCLE,
    NO_DELIVERY,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    PartialMonthCalculationModeDecider,
    "is_proportional_mode_active",
    autospec=True,
    return_value=True,
)
@patch.object(
    MonthlyDeliveryDateCounter, "count_delivery_dates_in_month", autospec=True
)
class TestBuildCalculationPartForSubscriptionWithinMonth(TapirUnitTest):
    OCTOBER = datetime.date(year=2026, month=10, day=1)
    NOVEMBER = datetime.date(year=2026, month=11, day=1)
    MONTHLY_PRICE = Decimal("95")
    PRICE_OF_SINGLE_DELIVERY = Decimal("21.51")

    @staticmethod
    def _build_subscription(
        delivery_cycle: str,
        start_date: datetime.date,
        end_date: datetime.date,
        quantity: int = 1,
    ) -> Subscription:
        return SubscriptionFactory.build(
            product__name="Kiste",
            product__type__name="Ernteanteil",
            product__type__delivery_cycle=delivery_cycle,
            start_date=start_date,
            end_date=end_date,
            quantity=quantity,
        )

    @staticmethod
    def _mock_delivery_dates(
        mock_count_delivery_dates_in_month: MagicMock,
        subscription_dates: int,
        total_dates: int,
    ) -> None:
        mock_count_delivery_dates_in_month.side_effect = lambda contract_start, **_: (
            total_dates if contract_start is None else subscription_dates
        )

    @classmethod
    def _get_part(
        cls, subscription: Subscription, first_of_month: datetime.date
    ) -> CalculationPart | None:
        return MonthPaymentBuilderSubscriptions._build_calculation_part_for_subscription_within_month(
            subscription=subscription,
            first_of_month=first_of_month,
            monthly_price=cls.MONTHLY_PRICE,
            price_of_single_delivery=cls.PRICE_OF_SINGLE_DELIVERY,
            cache={},
        )

    def test_buildCalculationPartForSubscriptionWithinMonth_subscriptionDoesNotOverlapMonth_returnsNone(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        subscription = self._build_subscription(
            delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=11, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

        self.assertIsNone(
            self._get_part(subscription=subscription, first_of_month=self.OCTOBER)
        )
        mock_count_delivery_dates_in_month.assert_not_called()
        mock_is_proportional_mode_active.assert_not_called()

    def test_buildCalculationPartForSubscriptionWithinMonth_customCycle_paysPerDeliveryEvenIfMonthIsFullyCovered(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        self._mock_delivery_dates(
            mock_count_delivery_dates_in_month, subscription_dates=3, total_dates=3
        )
        subscription = self._build_subscription(
            delivery_cycle=CUSTOM_CYCLE[0],
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(Decimal("64.53"), part.value)
        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste: 3 Lieferungen à 21,51 € = 64,53 €",
            part.explanation,
        )
        mock_is_proportional_mode_active.assert_not_called()

    def test_buildCalculationPartForSubscriptionWithinMonth_monthFullyCovered_returnsMonthlyPrice(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        subscription = self._build_subscription(
            delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(self.MONTHLY_PRICE, part.value)
        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste: 95,00 € monatlich (voller Monat)",
            part.explanation,
        )
        mock_count_delivery_dates_in_month.assert_not_called()
        mock_is_proportional_mode_active.assert_not_called()

    def test_buildCalculationPartForSubscriptionWithinMonth_weeklyPartialMonthWithFiveDates_returnsShareOfDeliveryDates(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        self._mock_delivery_dates(
            mock_count_delivery_dates_in_month, subscription_dates=4, total_dates=5
        )
        subscription = self._build_subscription(
            delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=10, day=26),
        )

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(Decimal("76"), part.value)
        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste: 95,00 € × 4 ÷ 5 Liefertermine = 76,00 €",
            part.explanation,
        )
        mock_is_proportional_mode_active.assert_called_once_with(
            first_of_month=self.OCTOBER, cache={}
        )

    def test_buildCalculationPartForSubscriptionWithinMonth_weeklyPartialMonthWithFourDates_returnsShareOfDeliveryDates(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        __: MagicMock,
    ):
        self._mock_delivery_dates(
            mock_count_delivery_dates_in_month, subscription_dates=3, total_dates=4
        )
        subscription = self._build_subscription(
            delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=11, day=9),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        part = self._get_part(subscription=subscription, first_of_month=self.NOVEMBER)

        self.assertEqual(Decimal("71.25"), part.value)

    def test_buildCalculationPartForSubscriptionWithinMonth_biweeklyPartialMonth_returnsShareOfDeliveryDates(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        __: MagicMock,
    ):
        self._mock_delivery_dates(
            mock_count_delivery_dates_in_month, subscription_dates=1, total_dates=3
        )
        subscription = self._build_subscription(
            delivery_cycle=EVEN_WEEKS[0],
            start_date=datetime.date(year=2026, month=10, day=20),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(self.MONTHLY_PRICE / 3, part.value)
        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste: 95,00 € × 1 ÷ 3 Liefertermine = 31,67 €",
            part.explanation,
        )

    def test_buildCalculationPartForSubscriptionWithinMonth_everyFourWeeksPartialMonthWithTheOnlyDate_returnsMonthlyPrice(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        __: MagicMock,
    ):
        self._mock_delivery_dates(
            mock_count_delivery_dates_in_month, subscription_dates=1, total_dates=1
        )
        subscription = self._build_subscription(
            delivery_cycle=EVERY_FOUR_WEEKS[0],
            start_date=datetime.date(year=2026, month=10, day=5),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(self.MONTHLY_PRICE, part.value)
        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste: 95,00 € × 1 ÷ 1 Liefertermin = 95,00 €",
            part.explanation,
        )

    def test_buildCalculationPartForSubscriptionWithinMonth_noDeliveryDateInMonth_returnsZero(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        __: MagicMock,
    ):
        self._mock_delivery_dates(
            mock_count_delivery_dates_in_month, subscription_dates=0, total_dates=0
        )
        subscription = self._build_subscription(
            delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=10, day=20),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(Decimal(0), part.value)
        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste: keine Liefertermine im Monat = 0,00 €",
            part.explanation,
        )

    def test_buildCalculationPartForSubscriptionWithinMonth_noDeliveryCycleInProportionalMode_returnsShareOfDays(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        __: MagicMock,
    ):
        subscription = self._build_subscription(
            delivery_cycle=NO_DELIVERY[0],
            start_date=datetime.date(year=2026, month=10, day=20),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(self.MONTHLY_PRICE * 12 / 31, part.value)
        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste: 95,00 € × 12 von 31 Tagen = 36,77 €",
            part.explanation,
        )
        mock_count_delivery_dates_in_month.assert_not_called()

    def test_buildCalculationPartForSubscriptionWithinMonth_noDeliveryCycleProportionalModeInactive_returnsMonthlyPrice(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        self._mock_delivery_dates(
            mock_count_delivery_dates_in_month, subscription_dates=0, total_dates=0
        )
        subscription = self._build_subscription(
            delivery_cycle=NO_DELIVERY[0],
            start_date=datetime.date(year=2026, month=10, day=20),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        mock_is_proportional_mode_active.return_value = False

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(self.MONTHLY_PRICE, part.value)

    def test_buildCalculationPartForSubscriptionWithinMonth_proportionalModeInactiveEnoughDeliveries_returnsMonthlyPrice(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        self._mock_delivery_dates(
            mock_count_delivery_dates_in_month, subscription_dates=4, total_dates=4
        )
        subscription = self._build_subscription(
            delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=10, day=8),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        mock_is_proportional_mode_active.return_value = False

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(self.MONTHLY_PRICE, part.value)
        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste: 95,00 € monatlich (4 Lieferungen, voller Monatspreis ab 4)",
            part.explanation,
        )

    def test_buildCalculationPartForSubscriptionWithinMonth_proportionalModeInactiveNotEnoughDeliveries_paysPerDelivery(
        self,
        mock_count_delivery_dates_in_month: MagicMock,
        mock_is_proportional_mode_active: MagicMock,
    ):
        self._mock_delivery_dates(
            mock_count_delivery_dates_in_month, subscription_dates=2, total_dates=4
        )
        subscription = self._build_subscription(
            delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=10, day=20),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        mock_is_proportional_mode_active.return_value = False

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(Decimal("43.02"), part.value)
        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste: 2 Lieferungen à 21,51 € = 43,02 €",
            part.explanation,
        )

    def test_buildCalculationPartForSubscriptionWithinMonth_quantityAboveOne_showsQuantityInName(
        self,
        _: MagicMock,
        __: MagicMock,
    ):
        subscription = self._build_subscription(
            delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
            quantity=2,
        )

        part = self._get_part(subscription=subscription, first_of_month=self.OCTOBER)

        self.assertEqual(
            "Oktober 2026, Ernteanteil Kiste (2 Anteile): 95,00 € monatlich (voller Monat)",
            part.explanation,
        )
