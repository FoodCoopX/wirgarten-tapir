from django_test_migrations.contrib.unittest_case import MigratorTestCase

MIGRATIONS_BEFORE = [
    ("wirgarten", "0152_product_unique_non_deleted_name"),
    ("tapir_mail", "0052_stable_trigger_ids"),
]
MIGRATIONS_TESTED = [("wirgarten", "0153_stable_onboarding_trigger_id")]


class StableOnboardingTriggerIdMigratorTestCase(MigratorTestCase):
    migrate_from = MIGRATIONS_BEFORE
    migrate_to = MIGRATIONS_TESTED

    def _create_version(self, trigger_ids: list[str]):
        email_configuration = self.old_state.apps.get_model(
            "tapir_mail", "EmailConfiguration"
        ).objects.create(name=f"Configuration {'-'.join(trigger_ids)}")
        return self.old_state.apps.get_model(
            "tapir_mail", "EmailConfigurationVersion"
        ).objects.create(
            email_configuration=email_configuration,
            triggers=[
                {"trigger_id": trigger_id, "trigger_field_values": {}}
                for trigger_id in trigger_ids
            ],
        )

    def _get_trigger_ids(self, version_id: str) -> list[str]:
        version = self.new_state.apps.get_model(
            "tapir_mail", "EmailConfigurationVersion"
        ).objects.get(id=version_id)
        return [trigger["trigger_id"] for trigger in version.triggers]
