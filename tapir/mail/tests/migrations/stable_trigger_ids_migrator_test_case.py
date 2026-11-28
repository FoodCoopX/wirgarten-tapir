from django_test_migrations.contrib.unittest_case import MigratorTestCase

MIGRATION_BEFORE = ("tapir_mail", "0051_layout_templates")
MIGRATION_TESTED = ("tapir_mail", "0052_stable_trigger_ids")


class StableTriggerIdsMigratorTestCase(MigratorTestCase):
    migrate_from = MIGRATION_BEFORE
    migrate_to = MIGRATION_TESTED

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
