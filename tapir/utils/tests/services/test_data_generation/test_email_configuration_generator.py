from tapir_mail.models import EmailConfigurationVersion
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.utils.services.test_data_generation.email_configuration_generator import (
    EmailConfigurationGenerator,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestEmailConfigurationGenerator(TapirIntegrationTest):
    def test_generateEmailConfigurations_bidTrigger_createsReleasedVersion(self):
        EmailConfigurationGenerator.generate_email_configurations()

        version = EmailConfigurationVersion.objects.filter(
            status="released",
            triggers__contains=[
                {
                    "trigger_id": TransactionalTrigger.get_id(),
                    "trigger_field_values": {"key": Events.BIDDING_ROUND_BID_RECEIVED},
                }
            ],
        ).first()

        self.assertIsNotNone(version)
        self.assertIn("<mjml>", version.content)
        self.assertEqual(["Alle Benutzer"], version.dynamic_segments_additive)

    def test_generateEmailConfigurations_runningTwice_doesNotDuplicateVersions(self):
        EmailConfigurationGenerator.generate_email_configurations()
        first_count = EmailConfigurationVersion.objects.count()
        self.assertGreater(first_count, 0)

        EmailConfigurationGenerator.generate_email_configurations()

        self.assertEqual(first_count, EmailConfigurationVersion.objects.count())
