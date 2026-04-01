from decimal import Decimal
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.subscriptions.config import (
    SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED,
    SOLIDARITY_MODE_ONLY_POSITIVE,
    SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestGetSolidarityContributionMinimum(SimpleTestCase):
    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_negativeAlwaysAllowed_returnsNone(
        self,
        mock_get_solidarity_excess: Mock,
        mock_get_parameter_value: Mock,
    ):
        mock_get_parameter_value.return_value = SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED
        cache = Mock()

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=Mock(), cache=cache
        )

        self.assertIsNone(result)
        mock_get_solidarity_excess.assert_not_called()
        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
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
        mock_get_parameter_value.return_value = SOLIDARITY_MODE_ONLY_POSITIVE
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
        mock_get_parameter_value.return_value = (
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE
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
        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )

    @patch(
        "tapir.solidarity_contribution.services.solidarity_validator.get_parameter_value",
        autospec=True,
    )
    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_solidarityExcessIsPositive_returnsNegativeExcess(
        self,
        mock_get_solidarity_excess: Mock,
        mock_get_parameter_value: Mock,
    ):
        mock_get_parameter_value.return_value = (
            SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE
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
        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
