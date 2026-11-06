from tapir_mail.models import EmailConfiguration, EmailConfigurationVersion
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger
from tapir.wirgarten.tapirmail import Segments


class EmailConfigurationGenerator:
    @classmethod
    def generate_email_configurations(cls):
        created_count = 0
        updated_count = 0
        for (
            key,
            display_name,
        ) in TransactionalTrigger.transactional_trigger_registry.items():
            default_content = (
                TransactionalTrigger.required_trigger_to_default_content_map.get(key)
            )
            if default_content is None:
                continue

            versions = cls._get_versions_for_trigger_key(key)
            if versions:
                for version in versions:
                    version.content = default_content
                    version.save()
                updated_count += 1
            else:
                cls._create_released_version(
                    key=key, display_name=display_name, content=default_content
                )
                created_count += 1

        print(
            f"Created {created_count} and updated {updated_count} default email configurations..."
        )

    @classmethod
    def _get_versions_for_trigger_key(cls, key: str) -> list:
        versions = []
        for version in EmailConfigurationVersion.objects.all():
            for trigger in version.triggers or []:
                if trigger.get("trigger_id") == TransactionalTrigger.get_id() and (
                    trigger.get("trigger_field_values", {}).get("key") == key
                ):
                    versions.append(version)
        return versions

    @classmethod
    def _create_released_version(
        cls, key: str, display_name: str, content: str
    ) -> None:
        email_configuration, _ = EmailConfiguration.objects.get_or_create(
            name=display_name,
            defaults={"description": "Default email configuration created by populate"},
        )
        version = EmailConfigurationVersion(
            email_configuration=email_configuration,
            content=content,
            subject=display_name,
            triggers=[
                {
                    "trigger_id": TransactionalTrigger.get_id(),
                    "trigger_field_values": {"key": key},
                }
            ],
            dynamic_segments_additive=[Segments.ALL_USERS],
        )
        version.release()
