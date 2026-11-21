import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_size_change_date_options_builder import (
    AdminSizeChangeDateOptionsBuilder,
)
from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.subscriptions.types import DateOption
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(
    AdminSizeChangeValidator,
    "is_change_from_next_period",
    autospec=True,
    return_value=True,
)
@patch.object(TapirCache, "get_all_growing_periods_ascending", autospec=True)
class TestAdminSizeChangeDateOptionsBuilderBuildNextPeriodOption(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.current_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        self.next_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2028, month=1, day=1),
            end_date=datetime.date(year=2028, month=12, day=31),
        )
        self.subscription = SubscriptionFactory.build(period=self.current_period)
        mock_timezone(test=self, now=datetime.datetime(year=2027, month=6, day=2))

    def test_buildNextPeriodOption_changeFromNextPeriodPossible_returnsEnabledOption(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_is_change_from_next_period: MagicMock,
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            self.current_period,
            self.next_period,
        ]
        cache = {}

        option = AdminSizeChangeDateOptionsBuilder.build_next_period_option(
            subscription=self.subscription, cache=cache
        )

        self.assertEqual(
            DateOption(date=self.next_period.start_date, enabled=True), option
        )
        mock_is_change_from_next_period.assert_called_once_with(
            subscription=self.subscription,
            change_date=self.next_period.start_date,
            cache=cache,
        )

    def test_buildNextPeriodOption_changeNotPossible_returnsDisabledOption(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_is_change_from_next_period: MagicMock,
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            self.current_period,
            self.next_period,
        ]
        mock_is_change_from_next_period.return_value = False

        option = AdminSizeChangeDateOptionsBuilder.build_next_period_option(
            subscription=self.subscription, cache={}
        )

        self.assertEqual(
            DateOption(date=self.next_period.start_date, enabled=False), option
        )

    def test_buildNextPeriodOption_subscriptionInNextPeriod_returnsEnabledOptionAtPeriodStart(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_is_change_from_next_period: MagicMock,
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            self.current_period,
            self.next_period,
        ]
        subscription = SubscriptionFactory.build(period=self.next_period)

        option = AdminSizeChangeDateOptionsBuilder.build_next_period_option(
            subscription=subscription, cache={}
        )

        self.assertEqual(
            DateOption(date=self.next_period.start_date, enabled=True), option
        )
        mock_is_change_from_next_period.assert_not_called()

    def test_buildNextPeriodOption_noNextPeriod_returnsDisabledOptionWithoutDate(
        self,
        mock_get_all_growing_periods_ascending: MagicMock,
        mock_is_change_from_next_period: MagicMock,
    ):
        mock_get_all_growing_periods_ascending.return_value = [self.current_period]

        option = AdminSizeChangeDateOptionsBuilder.build_next_period_option(
            subscription=self.subscription, cache={}
        )

        self.assertEqual(DateOption(date=None, enabled=False), option)
        mock_is_change_from_next_period.assert_not_called()
