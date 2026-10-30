from decimal import Decimal
from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from tapir.coop.services.coop_share_instalment_config_validator import (
    CoopShareInstalmentConfigValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch(
    "tapir.coop.services.coop_share_instalment_config_validator.get_parameter_value",
    autospec=True,
    return_value=50,
)
class TestCoopShareInstalmentConfigValidator(TapirUnitTest):
    def test_validateInstalmentAmount_sharePriceDivisibleByAmount_noError(
        self, mock_get_parameter_value: Mock
    ):
        CoopShareInstalmentConfigValidator.validate_instalment_amount(Decimal("12.5"))

        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.COOP_SHARE_PRICE
        )

    def test_validateInstalmentAmount_sharePriceNotDivisibleByAmount_raisesError(
        self, _: Mock
    ):
        with self.assertRaises(ValidationError):
            CoopShareInstalmentConfigValidator.validate_instalment_amount(Decimal(15))

    def test_validateInstalmentAmount_sharePriceParameterNotDefinedYet_noError(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.side_effect = KeyError()

        CoopShareInstalmentConfigValidator.validate_instalment_amount(Decimal(15))

    def test_validateInstalmentAmount_amountIsZero_noErrorRaisedHere(
        self, mock_get_parameter_value: Mock
    ):
        # The error will be raised by a min value validator instead.
        CoopShareInstalmentConfigValidator.validate_instalment_amount(Decimal(0))

        mock_get_parameter_value.assert_not_called()
