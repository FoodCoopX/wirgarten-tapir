import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.tests.factories import SubscriptionFactory


class TestGetNumberOfMonthsAndDeliveriesToPay(SimpleTestCase):
    @patch.object(MonthPaymentBuilder, "get_number_of_deliveries_in_month")
    def test_getNumberOfMonthsAndDeliveriesToPay_default_checksEveryMonthOfRangeCorrectly(
        self,
        mock_get_number_of_deliveries_in_month: Mock,
    ):
        range_start = datetime.date(2020, 1, 1)
        range_end = datetime.date(2020, 6, 30)
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(2020, 1, 7),
            end_date=datetime.date(2020, 6, 20),
            product__type__delivery_cycle=WEEKLY[0],
        )
        cache = Mock()

        mock_get_number_of_deliveries_in_month.side_effect = (
            lambda subscription, first_of_month, cache: (
                4 if first_of_month.month == 1 else 3
            )
        )

        number_of_months, number_of_deliveries = (
            MonthPaymentBuilder.get_number_of_months_and_deliveries_to_pay(
                range_start=range_start,
                range_end=range_end,
                subscription=subscription,
                cache=cache,
            )
        )

        self.assertEqual(
            number_of_months, 5
        )  # There are 4 full months: Feb, Mar, Apr, Mai. Jan is not full but has enough deliveries to be counted full.
        self.assertEqual(
            number_of_deliveries, 3
        )  # June doesn't have enough deliveries to be counted full so we count deliveries

        self.assertEqual(2, mock_get_number_of_deliveries_in_month.call_count)
        mock_get_number_of_deliveries_in_month.assert_has_calls(
            [
                call(
                    subscription=subscription,
                    first_of_month=datetime.date(2020, 1, 1),
                    cache=cache,
                ),
                call(
                    subscription=subscription,
                    first_of_month=datetime.date(2020, 6, 1),
                    cache=cache,
                ),
            ]
        )
