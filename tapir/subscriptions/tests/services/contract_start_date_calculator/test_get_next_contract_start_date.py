import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)


class TestGetNextContractStartDate(SimpleTestCase):
    @patch.object(ContractStartDateCalculator, "can_contract_start_on_date")
    def test_getNextContractStartDate_referenceDateIsNotMonday_returnsMonday(
        self, mock_can_contract_start_on_date: Mock
    ):
        mock_can_contract_start_on_date.return_value = True

        cache = {}
        input_date = datetime.date(year=2025, month=7, day=15)  # Tuesday
        result = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=input_date, cache=cache
        )

        self.assertEqual(0, result.weekday())
        self.assertEqual(datetime.date(year=2025, month=7, day=14), result)

    @patch.object(ContractStartDateCalculator, "can_contract_start_on_date")
    def test_getNextContractStartDate_default_returnsFirstMondayAfterTheDateLimit(
        self, mock_can_contract_start_on_date: Mock
    ):
        mock_can_contract_start_on_date.side_effect = (
            lambda reference_date, cache: reference_date
            > datetime.date(year=2025, month=8, day=2)
        )

        cache = {}
        input_date = datetime.date(year=2025, month=7, day=15)  # Tuesday
        result = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=input_date, cache=cache
        )

        self.assertEqual(0, result.weekday())
        self.assertEqual(datetime.date(year=2025, month=8, day=4), result)
