from tapir.mail.tests.migrations.stable_trigger_ids_migrator_test_case import (
    MIGRATION_BEFORE,
    MIGRATION_TESTED,
    StableTriggerIdsMigratorTestCase,
)


class TestStableTriggerIdsBackward(StableTriggerIdsMigratorTestCase):
    migrate_from = MIGRATION_TESTED
    migrate_to = MIGRATION_BEFORE

    def prepare(self):
        self.version = self._create_version(
            trigger_ids=["transactional_trigger", "time_trigger"]
        )

    def test_backward(self):
        self.assertEqual(
            [
                "tapir_mail.triggers.transactional_trigger.transactional_trigger",
                "tapir_mail.triggers.time_trigger.time_trigger",
            ],
            self._get_trigger_ids(self.version.id),
        )
