from unittest.mock import Mock, patch

from tapir.payments.services.payment_export_intended_use_builder import (
    PaymentExportIntendedUseBuilder,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildIntendedUse(TapirUnitTest):
    @patch.object(
        PaymentExportIntendedUseBuilder, "_build_intended_use_legacy", autospec=True
    )
    @patch.object(
        PaymentExportIntendedUseBuilder,
        "_build_intended_use_from_pattern",
        autospec=True,
    )
    def test_buildIntendedUse_customEnabled_callsFromPattern(
        self,
        mock_build_intended_use_from_pattern: Mock,
        mock_build_intended_use_legacy: Mock,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM,
            value=True,
        )
        mock_build_intended_use_from_pattern.return_value = "FROM_PATTERN"
        payment = Mock()

        result = PaymentExportIntendedUseBuilder.build_intended_use(
            payment=payment, is_contracts=True, cache=cache
        )

        self.assertEqual("FROM_PATTERN", result)
        mock_build_intended_use_from_pattern.assert_called_once_with(
            payment=payment, is_contracts=True, cache=cache
        )
        mock_build_intended_use_legacy.assert_not_called()

    @patch.object(
        PaymentExportIntendedUseBuilder, "_build_intended_use_legacy", autospec=True
    )
    @patch.object(
        PaymentExportIntendedUseBuilder,
        "_build_intended_use_from_pattern",
        autospec=True,
    )
    def test_buildIntendedUse_customDisabled_callsLegacy(
        self,
        mock_build_intended_use_from_pattern: Mock,
        mock_build_intended_use_legacy: Mock,
    ):
        mock_build_intended_use_legacy.return_value = "LEGACY"
        payment = Mock()
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM,
            value=False,
        )

        result = PaymentExportIntendedUseBuilder.build_intended_use(
            payment=payment, is_contracts=False, cache=cache
        )

        self.assertEqual("LEGACY", result)
        mock_build_intended_use_legacy.assert_called_once_with(
            is_contracts=False, payment=payment, cache=cache
        )
        mock_build_intended_use_from_pattern.assert_not_called()
