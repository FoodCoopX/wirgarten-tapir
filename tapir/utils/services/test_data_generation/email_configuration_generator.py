from tapir_mail.models import EmailConfiguration, EmailConfigurationVersion
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger
from tapir.wirgarten.tapirmail import Segments


class EmailConfigurationGenerator:
    @classmethod
    def generate_email_configurations(cls) -> None:
        created_count = 0
        updated_count = 0
        versions_by_trigger_key = cls._build_version_index()
        for (
            key,
            display_name,
        ) in TransactionalTrigger.transactional_trigger_registry.items():
            default_content = (
                TransactionalTrigger.required_trigger_to_default_content_map.get(key)
            )
            if default_content is None:
                continue

            versions = versions_by_trigger_key.get(key, [])
            if versions:
                for version in versions:
                    version.content = default_content
                    version.save()
                updated_count += len(versions)
            else:
                cls._create_released_version(
                    key=key, display_name=display_name, content=default_content
                )
                created_count += 1

        print(
            f"Created {created_count} and updated {updated_count} default email configurations..."
        )

    @classmethod
    def _build_version_index(cls) -> dict[str, list[EmailConfigurationVersion]]:
        versions_by_trigger_key: dict[str, list[EmailConfigurationVersion]] = {}
        for version in EmailConfigurationVersion.objects.all():
            for trigger in version.triggers or []:
                if trigger.get("trigger_id") != TransactionalTrigger.get_id():
                    continue
                key = trigger.get("trigger_field_values", {}).get("key")
                if key is None:
                    continue
                versions_by_trigger_key.setdefault(key, []).append(version)
        return versions_by_trigger_key

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
