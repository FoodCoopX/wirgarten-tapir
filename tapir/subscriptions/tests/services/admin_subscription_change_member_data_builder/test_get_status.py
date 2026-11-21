import datetime

from tapir.subscriptions.services.admin_subscription_change_member_data_builder import (
    AdminSubscriptionChangeMemberDataBuilder,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAdminSubscriptionChangeMemberDataBuilderGetStatus(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.subscription = SubscriptionFactory.build(
            period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2027, month=1, day=1),
                end_date=datetime.date(year=2027, month=12, day=31),
            )
        )

    def _get_status(self, today: datetime.date) -> str:
        return AdminSubscriptionChangeMemberDataBuilder.get_status(
            subscription=self.subscription, today=today
        )

    def test_getStatus_activeToday_returnsRunning(self):
        self.assertEqual(
            AdminSubscriptionChangeMemberDataBuilder.STATUS_RUNNING,
            self._get_status(today=datetime.date(year=2027, month=6, day=2)),
        )

    def test_getStatus_startsInTheFuture_returnsPlanned(self):
        self.assertEqual(
            AdminSubscriptionChangeMemberDataBuilder.STATUS_PLANNED,
            self._get_status(today=datetime.date(year=2026, month=11, day=19)),
        )

    def test_getStatus_cancelled_returnsCancelled(self):
        self.subscription.cancellation_ts = datetime.datetime(year=2027, month=3, day=1)

        self.assertEqual(
            AdminSubscriptionChangeMemberDataBuilder.STATUS_CANCELLED,
            self._get_status(today=datetime.date(year=2027, month=6, day=2)),
        )

    def test_getStatus_endedAndCancelled_returnsEnded(self):
        self.subscription.cancellation_ts = datetime.datetime(year=2027, month=3, day=1)

        self.assertEqual(
            AdminSubscriptionChangeMemberDataBuilder.STATUS_ENDED,
            self._get_status(today=datetime.date(year=2028, month=1, day=3)),
        )
