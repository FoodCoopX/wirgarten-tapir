import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from tapir.utils.dataclasses import CalculationPart
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetTotalToPay(TapirUnitTest):
    @patch.object(
        MonthPaymentBuilderSubscriptions,
        "get_calculation_parts",
        autospec=True,
        return_value=[
            CalculationPart(explanation="", value=Decimal(3)),
            CalculationPart(explanation="", value=Decimal("7.5")),
        ],
    )
    def test_getTotalToPay_default_returnsSumOfCalculationParts(
        self, mock_get_calculation_parts: MagicMock
    ):
        range_start = datetime.date(year=2028, month=1, day=1)
        range_end = datetime.date(year=2028, month=1, day=31)
        contracts = []
        cache = {}

        result = MonthPaymentBuilderSubscriptions.get_total_to_pay(
            range_start=range_start,
            range_end=range_end,
            contracts=contracts,
            cache=cache,
        )

        self.assertEqual(Decimal("10.5"), result)
        mock_get_calculation_parts.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            contracts=contracts,
            cache=cache,
        )
