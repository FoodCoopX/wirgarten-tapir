from decimal import Decimal
from unittest.mock import patch, Mock

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


class TestGetSolidarityContributionMinimum(TapirUnitTest):
    @staticmethod
    def build_parameter_values_getter(solidarity_mode: int, configured_minimum: str):
        parameter_values = {
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED: solidarity_mode,
            ParameterKeys.SOLIDARITY_MINIMUM: Decimal(configured_minimum),
        }
        return lambda key, cache: parameter_values[key]

    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_negativeAlwaysAllowed_returnsConfiguredMinimum(
        self,
        mock_get_solidarity_excess: Mock,
        mock_get_parameter_value: Mock,
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED, "-15"
        )
        cache = Mock()

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=Mock(), cache=cache
        )

        self.assertEqual(-15, result)
        mock_get_solidarity_excess.assert_not_called()
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
    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_onlyPositiveAllowed_returnsZero(
        self,
        mock_get_solidarity_excess: Mock,
        mock_get_parameter_value: Mock,
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_ONLY_POSITIVE, "-15"
        )
        cache = Mock()

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=Mock(), cache=cache
        )

        self.assertEqual(0, result)
        mock_get_solidarity_excess.assert_not_called()
        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )

    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_solidarityExcessIsNegative_returnsZero(
        self,
        mock_get_solidarity_excess: Mock,
        mock_get_parameter_value: Mock,
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal("-10")
        cache = Mock()
        reference_date = Mock()

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=reference_date, cache=cache
        )

        self.assertEqual(0, result)
        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=reference_date, cache=cache
        )

    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_solidarityExcessIsSmallerThanConfiguredMinimum_returnsNegativeExcess(
        self,
        mock_get_solidarity_excess: Mock,
        mock_get_parameter_value: Mock,
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal("10.51")
        cache = Mock()
        reference_date = Mock()

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=reference_date, cache=cache
        )

        self.assertEqual(-10.51, result)
        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=reference_date, cache=cache
        )

    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_solidarityExcessIsLargerThanConfiguredMinimum_returnsConfiguredMinimum(
        self,
        mock_get_solidarity_excess: Mock,
        mock_get_parameter_value: Mock,
    ):
        mock_get_parameter_value.side_effect = self.build_parameter_values_getter(
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal("200")
        cache = Mock()
        reference_date = Mock()

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=reference_date, cache=cache
        )

        self.assertEqual(-15, result)
        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=reference_date, cache=cache
        )
