import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_size_change_next_period_finder import (
    AdminSizeChangeNextPeriodFinder,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
@patch.object(TapirCache, "get_all_growing_periods_ascending", autospec=True)
class TestAdminSizeChangeNextPeriodFinderGetNextPeriodWithSubscriptions(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.member = MemberFactory.build()
        self.product = ProductFactory.build()
        self.subscription = SubscriptionFactory.build(
            member=self.member,
            product=self.product,
            period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2027, month=1, day=1),
                end_date=datetime.date(year=2027, month=12, day=31),
            ),
        )
        self.next_growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2028, month=1, day=1),
            end_date=datetime.date(year=2028, month=12, day=31),
        )
        self.next_period_subscription = SubscriptionFactory.build(
            member=self.member,
            product=ProductFactory.build(type=self.product.type),
            period=self.next_growing_period,
        )
        self.cache = {}

    def _get(self):
        return AdminSizeChangeNextPeriodFinder.get_next_period_with_subscriptions(
            member=self.member, subscription=self.subscription, cache=self.cache
        )

    def test_getNextPeriodWithSubscriptions_nextPeriodSubscriptionOfSameType_returnsNextPeriod(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_get_all_subscriptions_for_member: MagicMock,
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            self.subscription.period,
            self.next_growing_period,
        ]
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            self.next_period_subscription,
        ]

        self.assertEqual(self.next_growing_period, self._get())

        mock_get_all_growing_periods_ascending.assert_called_once_with(cache=self.cache)
        mock_get_all_subscriptions_for_member.assert_called_once_with(
            member_id=self.member.id, cache=self.cache
        )

    def test_getNextPeriodWithSubscriptions_onlyCurrentSubscriptions_returnsNone(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_get_all_subscriptions_for_member: MagicMock,
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            self.subscription.period,
            self.next_growing_period,
        ]
        mock_get_all_subscriptions_for_member.return_value = [self.subscription]

        self.assertIsNone(self._get())

    def test_getNextPeriodWithSubscriptions_nextPeriodSubscriptionCancelled_returnsNone(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_get_all_subscriptions_for_member: MagicMock,
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            self.subscription.period,
            self.next_growing_period,
        ]
        self.next_period_subscription.cancellation_ts = datetime.datetime(
            year=2027, month=5, day=1
        )
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            self.next_period_subscription,
        ]

        self.assertIsNone(self._get())

    def test_getNextPeriodWithSubscriptions_nextPeriodSubscriptionOfOtherType_returnsNone(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_get_all_subscriptions_for_member: MagicMock,
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            self.subscription.period,
            self.next_growing_period,
        ]
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            SubscriptionFactory.build(
                member=self.member, period=self.next_growing_period
            ),
        ]

        self.assertIsNone(self._get())

    def test_getNextPeriodWithSubscriptions_noNextGrowingPeriod_returnsNone(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_get_all_subscriptions_for_member: MagicMock,
    ):
        mock_get_all_growing_periods_ascending.return_value = [self.subscription.period]

        self.assertIsNone(self._get())

        mock_get_all_subscriptions_for_member.assert_not_called()

    def test_getNextPeriodWithSubscriptions_subscriptionEndsBeforePeriodEnd_returnsPeriodAfterIt(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_get_all_subscriptions_for_member: MagicMock,
    ):
        self.subscription.end_date = datetime.date(year=2027, month=6, day=6)
        mock_get_all_growing_periods_ascending.return_value = [
            self.subscription.period,
            self.next_growing_period,
        ]
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            self.next_period_subscription,
        ]

        self.assertEqual(self.next_growing_period, self._get())
