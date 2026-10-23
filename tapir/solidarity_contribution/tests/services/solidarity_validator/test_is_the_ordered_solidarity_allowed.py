from decimal import Decimal
from unittest.mock import Mock, patch

from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.subscriptions.config import (
    SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED,
    SOLIDARITY_MODE_ONLY_POSITIVE,
    SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestIsTheOrderedSolidarityAllowed(TapirUnitTest):
    @staticmethod
    def set_solidarity_parameters(
        cache: dict, solidarity_mode: int, configured_minimum: str | None = None
    ):
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED,
            value=solidarity_mode,
        )
        if configured_minimum is not None:
            mock_parameter_value(
                cache=cache,
                key=ParameterKeys.SOLIDARITY_MINIMUM,
                value=Decimal(configured_minimum),
            )

    def test_isTheOrderedSolidarityAllowed_positiveAmount_returnsTrue(self):
        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                1, start_date=Mock(), cache={}
            )
        )

    def test_isTheOrderedSolidarityAllowed_amountIsZero_returnsTrue(self):
        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                0, start_date=Mock(), cache={}
            )
        )

    def test_isTheOrderedSolidarityAllowed_modeNegativeAlwaysAllowedAndAmountEqualsConfiguredMinimum_returnsTrue(
        self,
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED, "-15"
        )

        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -15, start_date=Mock(), cache=cache
            )
        )

    def test_isTheOrderedSolidarityAllowed_modeNegativeAlwaysAllowedAndAmountIsBelowConfiguredMinimum_returnsFalse(
        self,
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED, "-15"
        )

        self.assertFalse(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -16, start_date=Mock(), cache=cache
            )
        )

    def test_isTheOrderedSolidarityAllowed_modeOnlyPositiveAllowedAndAmountIsNegative_returnsFalse(
        self,
    ):
        cache = {}
        self.set_solidarity_parameters(cache, SOLIDARITY_MODE_ONLY_POSITIVE)

        self.assertFalse(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -1, start_date=Mock(), cache=cache
            )
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_isTheOrderedSolidarityAllowed_modeDynamicButNotEnoughExcess_returnsFalse(
        self, mock_get_solidarity_excess: Mock
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal(12)
        start_date = Mock()

        self.assertFalse(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -13, start_date=start_date, cache=cache
            )
        )

        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=start_date, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_isTheOrderedSolidarityAllowed_modeDynamicAndEnoughExcess_returnsTrue(
        self, mock_get_solidarity_excess: Mock
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal(14)
        start_date = Mock()

        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -13, start_date=start_date, cache=cache
            )
        )

        self.assertEqual(2, mock_get_solidarity_excess.call_count)
        mock_get_solidarity_excess.assert_called_with(
            reference_date=start_date, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_isTheOrderedSolidarityAllowed_excessWouldAllowLowerAmountButAmountEqualsConfiguredMinimum_returnsTrue(
        self, mock_get_solidarity_excess: Mock
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal(200)
        start_date = Mock()

        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -15, start_date=start_date, cache=cache
            )
        )

        self.assertEqual(2, mock_get_solidarity_excess.call_count)
        mock_get_solidarity_excess.assert_called_with(
            reference_date=start_date, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_isTheOrderedSolidarityAllowed_excessWouldAllowLowerAmountButAmountIsBelowConfiguredMinimum_returnsFalse(
        self, mock_get_solidarity_excess: Mock
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal(200)
        start_date = Mock()

        self.assertFalse(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -16, start_date=start_date, cache=cache
            )
        )

        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=start_date, cache=cache
        )
