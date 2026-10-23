from decimal import Decimal
from unittest.mock import patch, Mock

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


class TestGetSolidarityContributionMinimum(TapirUnitTest):
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

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_negativeAlwaysAllowed_returnsConfiguredMinimum(
        self, mock_get_solidarity_excess: Mock
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED, "-15"
        )

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=Mock(), cache=cache
        )

        self.assertEqual(-15, result)
        mock_get_solidarity_excess.assert_not_called()

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_onlyPositiveAllowed_returnsZero(
        self, mock_get_solidarity_excess: Mock
    ):
        cache = {}
        self.set_solidarity_parameters(cache, SOLIDARITY_MODE_ONLY_POSITIVE)

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=Mock(), cache=cache
        )

        self.assertEqual(0, result)
        mock_get_solidarity_excess.assert_not_called()

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_solidarityExcessIsNegative_returnsZero(
        self, mock_get_solidarity_excess: Mock
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal("-10")
        reference_date = Mock()

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=reference_date, cache=cache
        )

        self.assertEqual(0, result)
        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=reference_date, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_solidarityExcessIsSmallerThanConfiguredMinimum_returnsNegativeExcess(
        self, mock_get_solidarity_excess: Mock
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal("10.51")
        reference_date = Mock()

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=reference_date, cache=cache
        )

        self.assertEqual(-10.51, result)
        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=reference_date, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess", autospec=True)
    def test_getSolidarityContributionMinimum_solidarityExcessIsLargerThanConfiguredMinimum_returnsConfiguredMinimum(
        self, mock_get_solidarity_excess: Mock
    ):
        cache = {}
        self.set_solidarity_parameters(
            cache, SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE, "-15"
        )
        mock_get_solidarity_excess.return_value = Decimal("200")
        reference_date = Mock()

        result = SolidarityValidator.get_solidarity_contribution_minimum(
            reference_date=reference_date, cache=cache
        )

        self.assertEqual(-15, result)
        mock_get_solidarity_excess.assert_called_once_with(
            reference_date=reference_date, cache=cache
        )
