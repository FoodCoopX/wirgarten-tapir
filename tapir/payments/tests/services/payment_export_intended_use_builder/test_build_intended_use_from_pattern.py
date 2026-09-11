from unittest.mock import Mock, patch

from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.payments.services.payment_export_intended_use_builder import (
    PaymentExportIntendedUseBuilder,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildIntendedUseFromPattern(TapirUnitTest):

    @patch.object(IntendedUsePatternExpander, "expand_pattern_contracts", autospec=True)
    @patch.object(
        PaymentExportIntendedUseBuilder, "_get_intended_use_case", autospec=True
    )
    def test_buildIntendedUseFromPattern_isContracts_callsExpandPatternContracts(
        self,
        mock_get_intended_use_case: Mock,
        mock_expand_pattern_contracts: Mock,
    ):
        mock_get_intended_use_case.return_value = (
            ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE
        )
        mock_expand_pattern_contracts.return_value = "expanded"
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE,
            value="test_pattern_contracts",
        )
        payment = Mock()

        result = PaymentExportIntendedUseBuilder._build_intended_use_from_pattern(
            payment=payment, is_contracts=True, cache=cache
        )

        self.assertEqual("expanded", result)
        mock_get_intended_use_case.assert_called_once_with(payment=payment, cache=cache)
        mock_expand_pattern_contracts.assert_called_once_with(
            pattern="test_pattern_contracts", payment=payment, cache=cache
        )

    @patch.object(
        IntendedUsePatternExpander, "expand_pattern_coop_shares_bought", autospec=True
    )
    def test_buildIntendedUseFromPattern_isCoopShares_callsExpandPatternCoopShares(
        self,
        mock_expand_pattern_coop_shares_bought: Mock,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PAYMENT_INTENDED_USE_COOP_SHARES,
            value="test_pattern_coop",
        )
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.COOP_SHARE_PRICE,
            value=50,
        )
        mock_expand_pattern_coop_shares_bought.return_value = "expanded"
        payment = Mock(amount=300)
        payment.mandate_ref.member = Mock()

        result = PaymentExportIntendedUseBuilder._build_intended_use_from_pattern(
            payment=payment, is_contracts=False, cache=cache
        )

        self.assertEqual("expanded", result)
        mock_expand_pattern_coop_shares_bought.assert_called_once_with(
            pattern="test_pattern_coop",
            member=payment.mandate_ref.member,
            number_of_shares=6,
            cache=cache,
        )
