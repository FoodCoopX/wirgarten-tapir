import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.wirgarten.tests.factories import SubscriptionFactory


class TestGetTotalToPay(SimpleTestCase):
    @patch.object(
        MonthPaymentBuilder, "get_amount_to_pay_for_subscription_within_range"
    )
    def test_getTotalToPay_default_considersOnlySubscriptionsThatOverlapWithTheGivenRange(
        self, mock_get_amount_to_pay_for_subscription_within_range: Mock
    ):
        range_start = datetime.date(year=2028, month=1, day=1)
        range_end = datetime.date(year=2028, month=1, day=31)
        subscription_1 = SubscriptionFactory.build(
            mandate_ref__ref="test_ref", start_date=range_start, end_date=range_end
        )
        subscription_2 = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2027, month=12, day=15),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        subscription_3 = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2027, month=12, day=15),
            end_date=datetime.date(year=2028, month=1, day=19),
        )

        total_to_pay_by_subscription = {
            subscription_1: 3,
            subscription_2: 5,
            subscription_3: 7,
        }

        mock_get_amount_to_pay_for_subscription_within_range.side_effect = lambda subscription, range_start, range_end, cache: total_to_pay_by_subscription[
            subscription
        ]
        cache = Mock()

        result = MonthPaymentBuilder.get_total_to_pay(
            range_start=range_start,
            range_end=range_end,
            subscriptions=[subscription_1, subscription_2, subscription_3],
            cache=cache,
        )

        self.assertEqual(3 + 7, result)
        self.assertEqual(
            2, mock_get_amount_to_pay_for_subscription_within_range.call_count
        )
        mock_get_amount_to_pay_for_subscription_within_range.assert_has_calls(
            [
                call(
                    subscription=subscription,
                    range_start=range_start,
                    range_end=range_end,
                    cache=cache,
                )
                for subscription in [subscription_1, subscription_3]
            ],
            any_order=True,
        )
