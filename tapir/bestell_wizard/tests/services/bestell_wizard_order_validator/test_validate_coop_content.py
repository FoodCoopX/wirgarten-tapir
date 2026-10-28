from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.coop.services.coop_share_instalment_order_validator import (
    CoopShareInstalmentOrderValidator,
)
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(CoopShareInstalmentOrderValidator, "validate_instalments", autospec=True)
@patch.object(
    MinimumNumberOfSharesValidator,
    "get_minimum_number_of_shares_for_tapir_order",
    autospec=True,
    return_value=2,
)
class TestValidateCoopContent(TapirUnitTest):
    def test_validateCoopContent_payInInstalments_validatesInstalments(
        self, _: Mock, mock_validate_instalments: Mock
    ):
        cache = {}

        BestellWizardOrderValidator.validate_coop_content(
            validated_data=self._build_validated_data(pay_in_instalments=True),
            order={},
            cache=cache,
        )

        mock_validate_instalments.assert_called_once_with(
            number_of_coop_shares=2, minimum_number_of_coop_shares=2, cache=cache
        )

    def test_validateCoopContent_noInstalments_instalmentsNotValidated(
        self, _: Mock, mock_validate_instalments: Mock
    ):
        BestellWizardOrderValidator.validate_coop_content(
            validated_data=self._build_validated_data(pay_in_instalments=False),
            order={},
            cache={},
        )

        mock_validate_instalments.assert_not_called()

    def test_validateCoopContent_studentPaysInInstalments_raisesError(self, *_: Mock):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
            value=True,
        )
        validated_data = self._build_validated_data(pay_in_instalments=True)
        validated_data["student_status_enabled"] = True
        validated_data["number_of_coop_shares"] = 0

        with self.assertRaises(ValidationError):
            BestellWizardOrderValidator.validate_coop_content(
                validated_data=validated_data, order={}, cache=cache
            )

    @staticmethod
    def _build_validated_data(pay_in_instalments: bool):
        return {
            "student_status_enabled": False,
            "number_of_coop_shares": 2,
            "statute_accepted": True,
            "pay_coop_shares_in_instalments": pay_in_instalments,
        }
