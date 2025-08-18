import datetime

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.wirgarten.tests.factories import SubscriptionFactory


class TestIsMonthFullyCoveredBySubscription(SimpleTestCase):
    def test_isMonthFullyCoveredBySubscription_givenMonthIsBeforeSubscription_returnsFalse(
        self,
    ):
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2027, month=8, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        result = MonthPaymentBuilder.is_month_fully_covered_by_subscription(
            subscription=subscription,
            first_of_month=datetime.date(year=2027, month=7, day=1),
        )

        self.assertFalse(result)

    def test_isMonthFullyCoveredBySubscription_givenMonthIsAfterSubscription_returnsFalse(
        self,
    ):
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2027, month=8, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        result = MonthPaymentBuilder.is_month_fully_covered_by_subscription(
            subscription=subscription,
            first_of_month=datetime.date(year=2028, month=1, day=1),
        )

        self.assertFalse(result)

    def test_isMonthFullyCoveredBySubscription_givenMonthIsStartOfSubscription_returnsTrue(
        self,
    ):
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2027, month=8, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        result = MonthPaymentBuilder.is_month_fully_covered_by_subscription(
            subscription=subscription,
            first_of_month=datetime.date(year=2027, month=8, day=1),
        )

        self.assertTrue(result)

    def test_isMonthFullyCoveredBySubscription_subscriptionStartsInTheMiddleOfGivenMonth_returnsFalse(
        self,
    ):
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2027, month=8, day=13),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        result = MonthPaymentBuilder.is_month_fully_covered_by_subscription(
            subscription=subscription,
            first_of_month=datetime.date(year=2027, month=8, day=1),
        )

        self.assertFalse(result)

    def test_isMonthFullyCoveredBySubscription_givenMonthIsEndOfSubscription_returnsTrue(
        self,
    ):
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2027, month=8, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        result = MonthPaymentBuilder.is_month_fully_covered_by_subscription(
            subscription=subscription,
            first_of_month=datetime.date(year=2027, month=12, day=1),
        )

        self.assertTrue(result)

    def test_isMonthFullyCoveredBySubscription_subscriptionEndsInTheMiddleOfGivenMonth_returnsFalse(
        self,
    ):
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2027, month=8, day=1),
            end_date=datetime.date(year=2027, month=12, day=15),
        )

        result = MonthPaymentBuilder.is_month_fully_covered_by_subscription(
            subscription=subscription,
            first_of_month=datetime.date(year=2027, month=12, day=31),
        )

        self.assertFalse(result)

    def test_isMonthFullyCoveredBySubscription_givenMonthIsFullyInsideSubscription_returnsTrue(
        self,
    ):
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2027, month=8, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

        result = MonthPaymentBuilder.is_month_fully_covered_by_subscription(
            subscription=subscription,
            first_of_month=datetime.date(year=2027, month=10, day=1),
        )

        self.assertTrue(result)
