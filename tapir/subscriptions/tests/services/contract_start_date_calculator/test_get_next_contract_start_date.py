import datetime
from unittest.mock import patch, Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestGetNextContractStartDate(TapirUnitTest):
    @patch.object(TapirCache, "get_growing_period_at_date", autospec=True)
    @patch.object(
        ContractStartDateCalculator, "can_contract_start_in_week", autospec=True
    )
    def test_getNextContractStartDate_referenceDateIsNotMonday_returnsMonday(
        self,
        mock_can_contract_start_in_week: Mock,
        mock_get_growing_period_at_date: Mock,
    ):
        mock_can_contract_start_in_week.return_value = True
        mock_get_growing_period_at_date.return_value = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2025, month=1, day=1)
        )

        cache = {}
        input_date = datetime.date(year=2025, month=7, day=15)  # Tuesday
        result = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=input_date, apply_buffer_time=True, cache=cache
        )

        self.assertEqual(0, result.weekday())
        self.assertEqual(datetime.date(year=2025, month=7, day=14), result)

    @patch.object(TapirCache, "get_growing_period_at_date", autospec=True)
    @patch.object(
        ContractStartDateCalculator, "can_contract_start_in_week", autospec=True
    )
    def test_getNextContractStartDate_default_returnsFirstMondayAfterTheDateLimit(
        self,
        mock_can_contract_start_in_week: Mock,
        mock_get_growing_period_at_date: Mock,
    ):
        mock_can_contract_start_in_week.side_effect = (
            lambda reference_date, apply_buffer_time, cache: reference_date
            > datetime.date(year=2025, month=8, day=2)
        )
        mock_get_growing_period_at_date.return_value = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2025, month=1, day=1)
        )

        cache = {}
        input_date = datetime.date(year=2025, month=7, day=15)  # Tuesday
        result = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=input_date, apply_buffer_time=True, cache=cache
        )

        self.assertEqual(0, result.weekday())
        self.assertEqual(datetime.date(year=2025, month=8, day=4), result)

    @patch.object(TapirCache, "get_growing_period_at_date", autospec=True)
    @patch.object(
        ContractStartDateCalculator, "can_contract_start_in_week", autospec=True
    )
    def test_getNextContractStartDate_givenDateIsAtTheStartOfGrowingPeriod_returnsFirstMondayAfterStartOfTheGrowingPeriod(
        self,
        mock_can_contract_start_in_week: Mock,
        mock_get_growing_period_at_date: Mock,
    ):
        # Contracts always start on a Monday, and prices usually change on the first day of each growing period.
        # If for example the first day of the growing period is a tuesday, the contract would start on the previous day,
        # so in the previous growing period, with the old prices.
        # It is important that contracts start on the growing period of the reference date
        # so that the new prices are used.

        mock_can_contract_start_in_week.return_value = True
        mock_get_growing_period_at_date.return_value = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2026, month=1, day=1)
        )

        cache = {}
        input_date = datetime.date(year=2026, month=1, day=1)  # Thursday
        result = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=input_date, apply_buffer_time=True, cache=cache
        )

        self.assertEqual(0, result.weekday())
        self.assertEqual(datetime.date(year=2026, month=1, day=5), result)

        mock_get_growing_period_at_date.assert_called_once_with(
            reference_date=input_date, cache=cache
        )
