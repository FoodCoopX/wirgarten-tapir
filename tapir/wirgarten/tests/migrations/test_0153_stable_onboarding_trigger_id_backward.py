from tapir.wirgarten.tests.migrations.stable_onboarding_trigger_id_migrator_test_case import (
    MIGRATIONS_BEFORE,
    MIGRATIONS_TESTED,
    StableOnboardingTriggerIdMigratorTestCase,
)


class TestStableOnboardingTriggerIdBackward(StableOnboardingTriggerIdMigratorTestCase):
    migrate_from = MIGRATIONS_TESTED
    migrate_to = MIGRATIONS_BEFORE

    def prepare(self):
        self.version = self._create_version(
            trigger_ids=["onboarding_trigger", "transactional_trigger"]
        )

    def test_backward(self):
        self.assertEqual(
            [
                "tapir.wirgarten.triggers.onboarding_trigger.onboarding_trigger",
                "transactional_trigger",
            ],
            self._get_trigger_ids(self.version.id),
        )
