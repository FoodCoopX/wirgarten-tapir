from unittest.mock import patch

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.configuration_generator import (
    ConfigurationGenerator,
)
from tapir.utils.services.test_data_generation.vierlande_generator import (
    VierlandeGenerator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestConfigurationGenerator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(VierlandeGenerator, "update_configuration", autospec=True)
    def test_updateSettingsForOrganization_enablesTheMembershipFeeWaiverOnlyForVierlande(
        self, mock_update_vierlande_configuration
    ):
        ConfigurationGenerator.update_settings_for_organization(Organization.VIERLANDE)

        self.assertTrue(
            get_parameter_value(
                key=ParameterKeys.ASSOCIATIONS_MEMBERSHIP_FEE_WAIVED_WITH_PRODUCTS,
                cache={},
            )
        )

        ConfigurationGenerator.update_settings_for_organization(Organization.BIOTOP)

        self.assertFalse(
            get_parameter_value(
                key=ParameterKeys.ASSOCIATIONS_MEMBERSHIP_FEE_WAIVED_WITH_PRODUCTS,
                cache={},
            )
        )
