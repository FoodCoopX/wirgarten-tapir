import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_size_change_date_options_builder import (
    AdminSizeChangeDateOptionsBuilder,
    DateOption,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(
    AdminSizeChangeDateOptionsBuilder,
    "build_next_period_option",
    autospec=True,
    return_value=DateOption(date=None, enabled=False),
)
@patch.object(
    AdminSizeChangeDateOptionsBuilder,
    "build_week_options",
    autospec=True,
    return_value=[],
)
@patch.object(
    ContractStartDateCalculator, "get_next_contract_start_date", autospec=True
)
class TestAdminSizeChangeDateOptionsBuilderBuild(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2027, month=6, day=2)
        )
        self.subscription = SubscriptionFactory.build(
            period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2027, month=1, day=1),
                end_date=datetime.date(year=2027, month=12, day=31),
            )
        )

    def test_build_nextPossibleStartWithinSubscription_enablesOptionA(
        self,
        mock_get_next_contract_start_date: MagicMock,
        mock_build_week_options: MagicMock,
        mock_build_next_period_option: MagicMock,
    ):
        next_possible_start = datetime.date(year=2027, month=6, day=14)
        mock_get_next_contract_start_date.return_value = next_possible_start
        cache = {}

        options = AdminSizeChangeDateOptionsBuilder.build(
            subscription=self.subscription, cache=cache
        )

        self.assertEqual(
            DateOption(date=next_possible_start, enabled=True),
            options.next_possible_start,
        )
        mock_get_next_contract_start_date.assert_called_once_with(
            reference_date=self.now.date(), apply_buffer_time=True, cache=cache
        )
        mock_build_week_options.assert_called_once_with(
            subscription=self.subscription,
            next_possible_start=next_possible_start,
            cache=cache,
        )
        mock_build_next_period_option.assert_called_once_with(
            subscription=self.subscription, cache=cache
        )

    def test_build_nextPossibleStartAfterSubscriptionEnd_disablesOptionA(
        self, mock_get_next_contract_start_date: MagicMock, *_: MagicMock
    ):
        self.subscription.end_date = datetime.date(year=2027, month=6, day=6)
        mock_get_next_contract_start_date.return_value = datetime.date(
            year=2027, month=6, day=14
        )

        options = AdminSizeChangeDateOptionsBuilder.build(
            subscription=self.subscription, cache={}
        )

        self.assertFalse(options.next_possible_start.enabled)
