import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestGetNextContractStartDateInGrowingPeriod(SimpleTestCase):
    @patch.object(ContractStartDateCalculator, "get_next_contract_start_date")
    def test_getNextContractStartDateInGrowingPeriod_growingPeriodIsAlreadyStarted_useTodayAsReferenceDate(
        self, mock_get_next_contract_start_date: Mock
    ):
        now = mock_timezone(self, now=datetime.datetime(year=2021, month=5, day=6))
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2021, month=1, day=1)
        )
        cache = {}
        start_date = Mock()
        mock_get_next_contract_start_date.return_value = start_date

        result = (
            ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period, cache=cache
            )
        )

        self.assertEqual(start_date, result)
        mock_get_next_contract_start_date.assert_called_once_with(
            reference_date=now.date(), apply_buffer_time=True, cache=cache
        )

    @patch.object(ContractStartDateCalculator, "get_next_contract_start_date")
    def test_getNextContractStartDateInGrowingPeriod_growingPeriodIsNotStartedYet_useGrowingPeriodStartAsReferenceDate(
        self, mock_get_next_contract_start_date: Mock
    ):
        mock_timezone(self, now=datetime.datetime(year=2021, month=5, day=6))
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2022, month=1, day=1)
        )
        cache = {}
        start_date = Mock()
        mock_get_next_contract_start_date.return_value = start_date

        result = (
            ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period, cache=cache
            )
        )

        self.assertEqual(start_date, result)
        mock_get_next_contract_start_date.assert_called_once_with(
            reference_date=growing_period.start_date,
            apply_buffer_time=True,
            cache=cache,
        )
