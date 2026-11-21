import datetime

from tapir.deliveries.services.partial_month_calculation_mode_decider import (
    PartialMonthCalculationModeDecider,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestIsProportionalModeActive(TapirUnitTest):
    @staticmethod
    def _build_cache() -> dict:
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PAYMENT_PARTIAL_MONTH_PROPORTIONAL_START_DATE,
            value=datetime.date(year=2027, month=3, day=1),
        )
        return cache

    def test_isProportionalModeActive_monthBeforeCutoff_returnsFalse(self):
        self.assertFalse(
            PartialMonthCalculationModeDecider.is_proportional_mode_active(
                first_of_month=datetime.date(year=2027, month=2, day=1),
                cache=self._build_cache(),
            )
        )

    def test_isProportionalModeActive_monthEqualToCutoff_returnsTrue(self):
        self.assertTrue(
            PartialMonthCalculationModeDecider.is_proportional_mode_active(
                first_of_month=datetime.date(year=2027, month=3, day=1),
                cache=self._build_cache(),
            )
        )

    def test_isProportionalModeActive_monthAfterCutoff_returnsTrue(self):
        self.assertTrue(
            PartialMonthCalculationModeDecider.is_proportional_mode_active(
                first_of_month=datetime.date(year=2027, month=4, day=1),
                cache=self._build_cache(),
            )
        )
