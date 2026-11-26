from tapir.mail.tests.migrations.stable_trigger_ids_migrator_test_case import (
    StableTriggerIdsMigratorTestCase,
)


class TestStableTriggerIdsForward(StableTriggerIdsMigratorTestCase):
    def prepare(self):
        self.version = self._create_version(
            trigger_ids=[
                "tapir_mail.triggers.transactional_trigger.transactional_trigger",
                "tapir_mail.triggers.time_trigger.time_trigger",
                "tapir.wirgarten.triggers.onboarding_trigger.onboarding_trigger",
            ]
        )

    def test_forward(self):
        self.assertEqual(
            [
                "transactional_trigger",
                "time_trigger",
                "tapir.wirgarten.triggers.onboarding_trigger.onboarding_trigger",
            ],
            self._get_trigger_ids(self.version.id),
        )
