import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    TapirCache,
    "get_growing_period_at_date",
    autospec=True,
    return_value=GrowingPeriodFactory.build(
        start_date=datetime.date(year=2028, month=1, day=1),
        end_date=datetime.date(year=2028, month=12, day=31),
    ),
)
class TestAdminSizeChangeValidatorIsChangeFromNextPeriod(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.subscription = SubscriptionFactory.build(
            period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2027, month=1, day=1),
                end_date=datetime.date(year=2027, month=12, day=31),
            )
        )

    def test_isChangeFromNextPeriod_dayAfterEndIsStartOfNextPeriod_returnsTrue(
        self, mock_get_growing_period_at_date: MagicMock
    ):
        change_date = datetime.date(year=2028, month=1, day=1)
        cache = {}

        result = AdminSizeChangeValidator.is_change_from_next_period(
            subscription=self.subscription, change_date=change_date, cache=cache
        )

        self.assertTrue(result)
        mock_get_growing_period_at_date.assert_called_once_with(
            reference_date=change_date, cache=cache
        )

    def test_isChangeFromNextPeriod_dateIsNotTheDayAfterEnd_returnsFalse(
        self, mock_get_growing_period_at_date: MagicMock
    ):
        result = AdminSizeChangeValidator.is_change_from_next_period(
            subscription=self.subscription,
            change_date=datetime.date(year=2028, month=1, day=3),
            cache={},
        )

        self.assertFalse(result)
        mock_get_growing_period_at_date.assert_not_called()

    def test_isChangeFromNextPeriod_subscriptionEndsBeforePeriodEnd_returnsFalse(
        self, _: MagicMock
    ):
        self.subscription.end_date = datetime.date(year=2027, month=6, day=6)

        result = AdminSizeChangeValidator.is_change_from_next_period(
            subscription=self.subscription,
            change_date=datetime.date(year=2027, month=6, day=7),
            cache={},
        )

        self.assertFalse(result)

    def test_isChangeFromNextPeriod_noGrowingPeriodAfterEnd_returnsFalse(
        self, mock_get_growing_period_at_date: MagicMock
    ):
        mock_get_growing_period_at_date.return_value = None

        result = AdminSizeChangeValidator.is_change_from_next_period(
            subscription=self.subscription,
            change_date=datetime.date(year=2028, month=1, day=1),
            cache={},
        )

        self.assertFalse(result)
