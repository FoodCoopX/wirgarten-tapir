import datetime
from unittest.mock import patch, MagicMock

from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetNumberOfDaysCoveredInMonth(TapirUnitTest):
    @patch.object(
        DateRangeOverlapChecker,
        "get_number_of_days_of_overlap",
        autospec=True,
        return_value=12,
    )
    def test_getNumberOfDaysCoveredInMonth_default_returnsOverlapBetweenMonthAndContract(
        self, mock_get_number_of_days_of_overlap: MagicMock
    ):
        contract_start = datetime.date(year=2028, month=2, day=18)
        contract_end = datetime.date(year=2028, month=12, day=31)

        result = MonthPaymentBuilderUtils.get_number_of_days_covered_in_month(
            first_of_month=datetime.date(year=2028, month=2, day=1),
            contract_start=contract_start,
            contract_end=contract_end,
        )

        self.assertEqual(12, result)
        mock_get_number_of_days_of_overlap.assert_called_once_with(
            range_1_start=contract_start,
            range_1_end=contract_end,
            range_2_start=datetime.date(year=2028, month=2, day=1),
            range_2_end=datetime.date(year=2028, month=2, day=29),
        )
