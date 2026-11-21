import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, call

from tapir.utils.dataclasses import CalculationPart
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetCalculationPartsForSubscriptionWithinRange(TapirUnitTest):
    @patch.object(
        SubscriptionPriceCalculator,
        "get_monthly_price",
        autospec=True,
        return_value=Decimal("14.5"),
    )
    @patch.object(
        DeliveryPriceCalculator,
        "get_price_of_single_delivery_for_subscription",
        autospec=True,
        return_value=Decimal("2.15"),
    )
    @patch.object(
        MonthPaymentBuilderSubscriptions,
        "_build_calculation_part_for_subscription_within_month",
        autospec=True,
    )
    def test_getCalculationPartsForSubscriptionWithinRange_default_returnsPartsOfEachCoveredMonth(
        self,
        mock_build_calculation_part_for_subscription_within_month: MagicMock,
        mock_get_price_of_single_delivery_for_subscription: MagicMock,
        mock_get_monthly_price: MagicMock,
    ):
        amounts_by_month = {
            datetime.date(2025, 1, 1): Decimal("14.5"),
            datetime.date(2025, 2, 1): Decimal("6.3"),
            datetime.date(2025, 3, 1): None,
        }
        mock_build_calculation_part_for_subscription_within_month.side_effect = (
            lambda first_of_month, **_: (
                None
                if amounts_by_month[first_of_month] is None
                else CalculationPart(
                    explanation=str(first_of_month),
                    value=amounts_by_month[first_of_month],
                )
            )
        )
        subscription = SubscriptionFactory.build()
        range_start = datetime.date(2025, 1, 1)
        cache = {}

        result = MonthPaymentBuilderSubscriptions._get_calculation_parts_for_subscription_within_range(
            subscription=subscription,
            range_start=range_start,
            range_end=datetime.date(2025, 3, 31),
            cache=cache,
        )

        self.assertEqual(
            [
                CalculationPart(explanation="2025-01-01", value=Decimal("14.5")),
                CalculationPart(explanation="2025-02-01", value=Decimal("6.3")),
            ],
            result,
        )
        mock_build_calculation_part_for_subscription_within_month.assert_has_calls(
            [
                call(
                    subscription=subscription,
                    first_of_month=first_of_month,
                    monthly_price=Decimal("14.5"),
                    price_of_single_delivery=Decimal("2.15"),
                    cache=cache,
                )
                for first_of_month in amounts_by_month.keys()
            ]
        )
        self.assertEqual(
            3, mock_build_calculation_part_for_subscription_within_month.call_count
        )
        mock_get_price_of_single_delivery_for_subscription.assert_called_once_with(
            subscription=subscription, at_date=range_start, cache=cache
        )
        mock_get_monthly_price.assert_called_once_with(
            subscription=subscription, reference_date=range_start, cache=cache
        )
