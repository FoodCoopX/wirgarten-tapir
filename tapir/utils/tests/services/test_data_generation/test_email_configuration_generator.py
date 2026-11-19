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

    def test_generateEmailConfigurations_configurationWithoutVersionExists_reusesConfiguration(
        self,
    ):
        display_name = "Mail-Kategorie-Registrierung - Bestätigung erforderlich"
        configuration = EmailConfiguration.objects.create(name=display_name)

        EmailConfigurationGenerator.generate_email_configurations()

        self.assertEqual(
            1, EmailConfiguration.objects.filter(name=display_name).count()
        )
        self.assertTrue(
            EmailConfigurationVersion.objects.filter(
                email_configuration=configuration
            ).exists()
        )
