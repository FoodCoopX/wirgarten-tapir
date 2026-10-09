from decimal import Decimal
from unittest.mock import Mock, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.subscriptions.config import (
    SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED,
    SOLIDARITY_MODE_ONLY_POSITIVE,
    SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestIsTheOrderedSolidarityAllowed(TapirUnitTest):
    @staticmethod
    def build_parameter_values_getter(solidarity_mode: int, configured_minimum: str):
        parameter_values = {
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED: solidarity_mode,
            ParameterKeys.SOLIDARITY_MINIMUM: Decimal(configured_minimum),
        }
        return lambda key, cache: parameter_values[key]

    def test_isTheOrderedSolidarityAllowed_positiveAmount_returnsTrue(self):
        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                1, start_date=Mock(), cache=Mock()
            )
        )

    def test_isTheOrderedSolidarityAllowed_amountIsZero_returnsTrue(self):
        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                0, start_date=Mock(), cache=Mock()
            )
        )

    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    def test_isTheOrderedSolidarityAllowed_modeNegativeAlwaysAllowedAndAmountEqualsConfiguredMinimum_returnsTrue(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED, "-15"
        )
        cache = Mock()
        start_date = Mock()

        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -15, start_date=start_date, cache=cache
            )
        )

        self.assertEqual(3, mock_get_parameter_value.call_count)
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.SOLIDARITY_MINIMUM, cache=cache
        )

    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    def test_isTheOrderedSolidarityAllowed_modeNegativeAlwaysAllowedAndAmountIsBelowConfiguredMinimum_returnsFalse(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED, "-15"
        )
        cache = Mock()
        start_date = Mock()

        self.assertFalse(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -16, start_date=start_date, cache=cache
            )
        )

        self.assertEqual(2, mock_get_parameter_value.call_count)
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.SOLIDARITY_MINIMUM, cache=cache
        )

    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    def test_isTheOrderedSolidarityAllowed_modeOnlyPositiveAllowedAndAmountIsNegative_returnsFalse(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = SOLIDARITY_MODE_ONLY_POSITIVE
        cache = Mock()

        self.assertFalse(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -1, start_date=Mock(), cache=cache
            )
        )

        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    def test_isTheOrderedSolidarityAllowed_modeDynamicButNotEnoughExcess_returnsFalse(
        self, mock_get_parameter_value: Mock, mock_get_solidarity_excess: Mock
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal(12)
        cache = Mock()
        start_date = Mock()

        self.assertFalse(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -13, start_date=start_date, cache=cache
            )
        )

        self.assertEqual(2, mock_get_parameter_value.call_count)
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.SOLIDARITY_MINIMUM, cache=cache
        )
        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=start_date, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    def test_isTheOrderedSolidarityAllowed_modeDynamicAndEnoughExcess_returnsTrue(
        self, mock_get_parameter_value: Mock, mock_get_solidarity_excess: Mock
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal(14)
        cache = Mock()
        start_date = Mock()

        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -13, start_date=start_date, cache=cache
            )
        )

        self.assertEqual(3, mock_get_parameter_value.call_count)
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.SOLIDARITY_MINIMUM, cache=cache
        )
        self.assertEqual(2, mock_get_solidarity_excess.call_count)
        mock_get_solidarity_excess.assert_called_with(
            reference_date=start_date, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    def test_isTheOrderedSolidarityAllowed_excessWouldAllowLowerAmountButAmountEqualsConfiguredMinimum_returnsTrue(
        self, mock_get_parameter_value: Mock, mock_get_solidarity_excess: Mock
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal(200)
        cache = Mock()
        start_date = Mock()

        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -15, start_date=start_date, cache=cache
            )
        )

        self.assertEqual(3, mock_get_parameter_value.call_count)
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.SOLIDARITY_MINIMUM, cache=cache
        )
        self.assertEqual(2, mock_get_solidarity_excess.call_count)
        mock_get_solidarity_excess.assert_called_with(
            reference_date=start_date, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    def test_isTheOrderedSolidarityAllowed_excessWouldAllowLowerAmountButAmountIsBelowConfiguredMinimum_returnsFalse(
        self, mock_get_parameter_value: Mock, mock_get_solidarity_excess: Mock
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal(200)
        cache = Mock()
        start_date = Mock()

        self.assertFalse(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -16, start_date=start_date, cache=cache
            )
        )

        self.assertEqual(2, mock_get_parameter_value.call_count)
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        mock_get_parameter_value.assert_any_call(
            key=ParameterKeys.SOLIDARITY_MINIMUM, cache=cache
        )
        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=start_date, cache=cache
        )
