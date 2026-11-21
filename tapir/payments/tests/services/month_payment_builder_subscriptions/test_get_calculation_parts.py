import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, call

from tapir.utils.dataclasses import CalculationPart
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetCalculationParts(TapirUnitTest):
    @patch.object(
        MonthPaymentBuilderSubscriptions,
        "_get_calculation_parts_for_subscription_within_range",
        autospec=True,
    )
    def test_getCalculationParts_default_returnsPartsOfOverlappingSubscriptionsSortedByStartDate(
        self, mock_get_calculation_parts_for_subscription_within_range: MagicMock
    ):
        range_start = datetime.date(year=2028, month=1, day=1)
        range_end = datetime.date(year=2028, month=1, day=31)
        subscription_starting_later = SubscriptionFactory.build(
            start_date=datetime.date(year=2028, month=1, day=20), end_date=range_end
        )
        subscription_outside_range = SubscriptionFactory.build(
            start_date=datetime.date(year=2027, month=12, day=15),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        subscription_starting_earlier = SubscriptionFactory.build(
            start_date=datetime.date(year=2027, month=12, day=15),
            end_date=datetime.date(year=2028, month=1, day=19),
        )
        parts_by_subscription = {
            subscription_starting_later: [
                CalculationPart(explanation="later", value=Decimal(3))
            ],
            subscription_starting_earlier: [
                CalculationPart(explanation="earlier", value=Decimal(7))
            ],
        }
        mock_get_calculation_parts_for_subscription_within_range.side_effect = (
            lambda subscription, **_: parts_by_subscription[subscription]
        )
        cache = {}

        result = MonthPaymentBuilderSubscriptions.get_calculation_parts(
            range_start=range_start,
            range_end=range_end,
            contracts=[
                subscription_starting_later,
                subscription_outside_range,
                subscription_starting_earlier,
            ],
            cache=cache,
        )

        self.assertEqual(["earlier", "later"], [part.explanation for part in result])
        self.assertEqual(
            2, mock_get_calculation_parts_for_subscription_within_range.call_count
        )
        mock_get_calculation_parts_for_subscription_within_range.assert_has_calls(
            [
                call(
                    subscription=subscription,
                    range_start=range_start,
                    range_end=range_end,
                    cache=cache,
                )
                for subscription in [
                    subscription_starting_earlier,
                    subscription_starting_later,
                ]
            ]
        )
