from django.db import migrations

OLD_TO_NEW_TRIGGER_IDS = {
    "tapir_mail.triggers.transactional_trigger.transactional_trigger": "transactional_trigger",
    "tapir_mail.triggers.time_trigger.time_trigger": "time_trigger",
}


def rename_trigger_ids(apps, mapping: dict[str, str]):
    EmailConfigurationVersion = apps.get_model(
        "tapir_mail", "EmailConfigurationVersion"
    )
    versions_to_update = []
    for version in EmailConfigurationVersion.objects.exclude(triggers=None):
        changed = False
        for trigger in version.triggers:
            if trigger.get("trigger_id") in mapping:
                trigger["trigger_id"] = mapping[trigger["trigger_id"]]
                changed = True
        if changed:
            versions_to_update.append(version)
    EmailConfigurationVersion.objects.bulk_update(versions_to_update, ["triggers"])


def forwards(apps, schema_editor):
    rename_trigger_ids(apps, OLD_TO_NEW_TRIGGER_IDS)


def backwards(apps, schema_editor):
    rename_trigger_ids(apps, {new: old for old, new in OLD_TO_NEW_TRIGGER_IDS.items()})


class Migration(migrations.Migration):
    dependencies = [
        ("tapir_mail", "0051_layout_templates"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
