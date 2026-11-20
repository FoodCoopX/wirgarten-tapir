from tapir_mail.models import EmailConfiguration, EmailConfigurationVersion

from tapir.utils.services.test_data_generation.email_configuration_generator import (
    EmailConfigurationGenerator,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestEmailConfigurationGenerator(TapirIntegrationTest):
    def test_generateEmailConfigurations_createsAndIsIdempotent(self):
        EmailConfigurationGenerator.generate_email_configurations()
        configuration_count = EmailConfiguration.objects.count()
        version_count = EmailConfigurationVersion.objects.count()
        self.assertGreater(configuration_count, 0)
        self.assertGreater(version_count, 0)

        EmailConfigurationGenerator.generate_email_configurations()

        self.assertEqual(configuration_count, EmailConfiguration.objects.count())
        self.assertEqual(version_count, EmailConfigurationVersion.objects.count())
