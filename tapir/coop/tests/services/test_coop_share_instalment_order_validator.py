from django.core.exceptions import ValidationError

from tapir.coop.services.coop_share_instalment_order_validator import (
    CoopShareInstalmentOrderValidator,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestCoopShareInstalmentOrderValidator(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.cache = {}
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.COOP_SHARES_INSTALMENTS_ENABLED,
            value=True,
        )

    def test_validateInstalments_numberOfSharesIsTheMinimum_noError(self):
        CoopShareInstalmentOrderValidator.validate_instalments(
            number_of_coop_shares=3, minimum_number_of_coop_shares=3, cache=self.cache
        )

    def test_validateInstalments_moreSharesThanTheMinimum_raisesError(self):
        with self.assertRaises(ValidationError):
            CoopShareInstalmentOrderValidator.validate_instalments(
                number_of_coop_shares=4,
                minimum_number_of_coop_shares=3,
                cache=self.cache,
            )

    def test_validateInstalments_instalmentsDisabled_raisesError(self):
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.COOP_SHARES_INSTALMENTS_ENABLED,
            value=False,
        )

        with self.assertRaises(ValidationError):
            CoopShareInstalmentOrderValidator.validate_instalments(
                number_of_coop_shares=3,
                minimum_number_of_coop_shares=3,
                cache=self.cache,
            )
