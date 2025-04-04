import datetime

from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, ODD_WEEKS
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    GrowingPeriodFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetSubscriptionsThatGetDeliveredInWeek(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=1, day=31),
        )
        # creating a subscription from another member to make sure it doesn't get included
        SubscriptionFactory.create(period=cls.growing_period)

    def test_getSubscriptionsThatGetDeliveredInWeek_deliveryCycleWeekly_subscriptionIncluded(
        self,
    ):
        member = MemberFactory.create()
        subscription = SubscriptionFactory.create(
            period=self.growing_period,
            product__type__delivery_cycle=WEEKLY[0],
            member=member,
        )

        result = DeliveryPriceCalculator.get_subscriptions_that_get_delivered_in_week(
            member, datetime.date(year=2025, month=1, day=15)
        )

        self.assertEqual(1, result.count())
        self.assertEqual(subscription, result.get())

    def test_getSubscriptionsThatGetDeliveredInWeek_deliveryCycleNotThisWeek_subscriptionNotIncluded(
        self,
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            period=self.growing_period,
            product__type__delivery_cycle=EVEN_WEEKS[0],
            member=member,
        )

        result = DeliveryPriceCalculator.get_subscriptions_that_get_delivered_in_week(
            member, datetime.date(year=2025, month=1, day=15)
        )

        self.assertEqual(0, result.count())

    def test_getSubscriptionsThatGetDeliveredInWeek_deliveryCycleThisWeek_subscriptionIncluded(
        self,
    ):
        member = MemberFactory.create()
        subscription = SubscriptionFactory.create(
            period=self.growing_period,
            product__type__delivery_cycle=ODD_WEEKS[0],
            member=member,
        )

        result = DeliveryPriceCalculator.get_subscriptions_that_get_delivered_in_week(
            member, datetime.date(year=2025, month=1, day=15)
        )

        self.assertEqual(1, result.count())
        self.assertEqual(subscription, result.get())
