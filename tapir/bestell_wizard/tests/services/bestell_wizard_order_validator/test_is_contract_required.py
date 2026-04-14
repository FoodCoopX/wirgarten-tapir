from django.test import SimpleTestCase

from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import ProductFactory


class TestIsContractRequired(SimpleTestCase):
    def test_isContractRequired_orderIsEmpty_returnsFalse(self):
        result = BestellWizardOrderValidator.is_contract_required(order={}, cache={})

        self.assertFalse(result)

    def test_isContractRequired_contractPolicyIsDefinedAsEmpty_returnsFalse(self):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.BESTELLWIZARD_CONTRACT_POLICY_CHECKBOX_TEXT,
            value="",
        )
        result = BestellWizardOrderValidator.is_contract_required(
            order={ProductFactory.build(): 2}, cache=cache
        )

        self.assertFalse(result)

    def test_isContractRequired_bothOrderAndContractPolicyAreNotEmpty_returnsTrue(self):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.BESTELLWIZARD_CONTRACT_POLICY_CHECKBOX_TEXT,
            value="not empty",
        )
        result = BestellWizardOrderValidator.is_contract_required(
            order={ProductFactory.build(): 2}, cache=cache
        )

        self.assertTrue(result)
