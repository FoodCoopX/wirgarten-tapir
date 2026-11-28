from django.db import migrations

OLD_TRIGGER_ID = "tapir.wirgarten.triggers.onboarding_trigger.onboarding_trigger"
NEW_TRIGGER_ID = "onboarding_trigger"


def rename_trigger_id(apps, old_trigger_id: str, new_trigger_id: str):
    EmailConfigurationVersion = apps.get_model(
        "tapir_mail", "EmailConfigurationVersion"
    )
    versions_to_update = []
    for version in EmailConfigurationVersion.objects.exclude(triggers=None):
        changed = False
        for trigger in version.triggers:
            if trigger.get("trigger_id") == old_trigger_id:
                trigger["trigger_id"] = new_trigger_id
                changed = True
        if changed:
            versions_to_update.append(version)
    EmailConfigurationVersion.objects.bulk_update(versions_to_update, ["triggers"])


def forwards(apps, schema_editor):
    rename_trigger_id(
        apps, old_trigger_id=OLD_TRIGGER_ID, new_trigger_id=NEW_TRIGGER_ID
    )


def backwards(apps, schema_editor):
    rename_trigger_id(
        apps, old_trigger_id=NEW_TRIGGER_ID, new_trigger_id=OLD_TRIGGER_ID
    )


class Migration(migrations.Migration):
    dependencies = [
        ("wirgarten", "0152_product_unique_non_deleted_name"),
        ("tapir_mail", "0052_stable_trigger_ids"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
