import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_subscription_addition_date_options_builder import (
    AdminSubscriptionAdditionDateOptionsBuilder,
)
from tapir.subscriptions.services.admin_subscription_addition_validator import (
    AdminSubscriptionAdditionValidator,
)
from tapir.subscriptions.services.start_date_week_options_builder import (
    StartDateWeekOptionsBuilder,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.types import DateOption
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory, ProductTypeFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(
    StartDateWeekOptionsBuilder,
    "build_week_options",
    autospec=True,
    return_value=[],
)
@patch.object(TapirCache, "get_first_growing_period_starting_after", autospec=True)
@patch.object(
    AdminSubscriptionAdditionValidator, "get_last_possible_start_date", autospec=True
)
@patch.object(
    ContractStartDateCalculator,
    "get_next_contract_start_date",
    autospec=True,
    return_value=datetime.date(year=2027, month=6, day=14),
)
class TestAdminSubscriptionAdditionDateOptionsBuilderBuild(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2027, month=6, day=2)
        )
        self.product_type = ProductTypeFactory.build()
        self.next_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2028, month=1, day=1),
            end_date=datetime.date(year=2028, month=12, day=31),
        )

    def test_build_nextPeriodExists_offersAllOptionsUntilLastPossibleStartDate(
        self,
        _: MagicMock,
        mock_get_last_possible_start_date: MagicMock,
        mock_get_first_growing_period_starting_after: MagicMock,
        mock_build_week_options: MagicMock,
    ):
        mock_get_last_possible_start_date.return_value = self.next_period.end_date
        mock_get_first_growing_period_starting_after.return_value = self.next_period
        cache = {}

        options = AdminSubscriptionAdditionDateOptionsBuilder.build(
            product_type=self.product_type, cache=cache
        )

        self.assertEqual(
            DateOption(date=datetime.date(year=2027, month=6, day=14), enabled=True),
            options.next_possible_start,
        )
        self.assertEqual(
            DateOption(date=self.next_period.start_date, enabled=True),
            options.next_period_start,
        )
        mock_build_week_options.assert_called_once_with(
            product_type=self.product_type,
            first_date=self.now.date(),
            last_date=self.next_period.end_date,
            next_possible_start=datetime.date(year=2027, month=6, day=14),
            cache=cache,
        )

    def test_build_noNextPeriod_disablesNextPeriodStartOptionWithoutDate(
        self,
        _: MagicMock,
        mock_get_last_possible_start_date: MagicMock,
        mock_get_first_growing_period_starting_after: MagicMock,
        __: MagicMock,
    ):
        mock_get_last_possible_start_date.return_value = datetime.date(
            year=2027, month=12, day=31
        )
        mock_get_first_growing_period_starting_after.return_value = None

        options = AdminSubscriptionAdditionDateOptionsBuilder.build(
            product_type=self.product_type, cache={}
        )

        self.assertEqual(
            DateOption(date=None, enabled=False), options.next_period_start
        )

    def test_build_noGrowingPeriod_offersNothing(
        self,
        _: MagicMock,
        mock_get_last_possible_start_date: MagicMock,
        mock_get_first_growing_period_starting_after: MagicMock,
        mock_build_week_options: MagicMock,
    ):
        mock_get_last_possible_start_date.return_value = None
        mock_get_first_growing_period_starting_after.return_value = None

        options = AdminSubscriptionAdditionDateOptionsBuilder.build(
            product_type=self.product_type, cache={}
        )

        self.assertFalse(options.next_possible_start.enabled)
        self.assertEqual([], options.weeks)
        mock_build_week_options.assert_not_called()
