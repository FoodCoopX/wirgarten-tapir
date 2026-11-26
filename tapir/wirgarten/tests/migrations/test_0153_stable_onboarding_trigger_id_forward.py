from tapir.wirgarten.tests.migrations.stable_onboarding_trigger_id_migrator_test_case import (
    StableOnboardingTriggerIdMigratorTestCase,
)


class TestStableOnboardingTriggerIdForward(StableOnboardingTriggerIdMigratorTestCase):
    def prepare(self):
        self.version = self._create_version(
            trigger_ids=[
                "tapir.wirgarten.triggers.onboarding_trigger.onboarding_trigger",
                "transactional_trigger",
            ]
        )

    def test_forward(self):
        self.assertEqual(
            ["onboarding_trigger", "transactional_trigger"],
            self._get_trigger_ids(self.version.id),
        )
