import datetime
from unittest.mock import patch, Mock, call

from tapir.deliveries.services.monthly_delivery_date_counter import (
    MonthlyDeliveryDateCounter,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetNumberOfMonthsAndDeliveriesToPay(TapirUnitTest):
    @patch.object(
        MonthlyDeliveryDateCounter,
        "count_delivery_dates_in_month",
        autospec=True,
    )
    def test_getNumberOfMonthsAndDeliveriesToPay_default_checksEveryMonthOfRangeCorrectly(
        self,
        mock_count_delivery_dates_in_month: Mock,
    ):
        range_start = datetime.date(2020, 1, 1)
        range_end = datetime.date(2020, 6, 30)
        subscription = SubscriptionFactory.build(
            start_date=datetime.date(2020, 1, 7),
            end_date=datetime.date(2020, 6, 20),
            product__type__delivery_cycle=WEEKLY[0],
        )
        cache = Mock()

        mock_count_delivery_dates_in_month.side_effect = lambda first_of_month, **_: (
            4 if first_of_month.month == 1 else 3
        )

        number_of_months, number_of_deliveries = (
            MonthPaymentBuilderSubscriptions.get_number_of_months_and_deliveries_to_pay(
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

        self.assertEqual(2, mock_count_delivery_dates_in_month.call_count)
        mock_count_delivery_dates_in_month.assert_has_calls(
            [
                call(
                    member_id=subscription.member_id,
                    product_type=subscription.product.type,
                    first_of_month=first_of_month,
                    contract_start=subscription.start_date,
                    contract_end=subscription.end_date,
                    cache=cache,
                )
                for first_of_month in [
                    datetime.date(2020, 1, 1),
                    datetime.date(2020, 6, 1),
                ]
            ]
        )
