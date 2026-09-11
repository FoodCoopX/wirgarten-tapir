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
    def test_isTheOrderedSolidarityAllowed_modeNegativeAlwaysAllowed_returnsTrue(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED
        cache = Mock()

        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -1000, start_date=Mock(), cache=cache
            )
        )

        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
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
        mock_get_parameter_value.return_value = (
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE
        )
        mock_get_solidarity_excess.return_value = Decimal(12)
        cache = Mock()
        start_date = Mock()

        self.assertFalse(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -13, start_date=start_date, cache=cache
            )
        )

        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
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
        mock_get_parameter_value.return_value = (
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE
        )
        mock_get_solidarity_excess.return_value = Decimal(14)
        cache = Mock()
        start_date = Mock()

        self.assertTrue(
            SolidarityValidator.is_the_ordered_solidarity_allowed(
                -13, start_date=start_date, cache=cache
            )
        )

        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=start_date, cache=cache
        )
