from django.db import migrations

RENAMED_SEGMENTS = {
    "Mit laufendem Ertevertrag": "Mit laufendem Vertrag (alle Produkte)",
    "Ohne laufenden Ertevertrag": "Ohne laufenden Vertrag (alle Produkte)",
}


def rename_segments(apps, renamed_segments: dict[str, str]):
    mail_category_class = apps.get_model("tapir_mail", "MailCategory")
    for old_name, new_name in renamed_segments.items():
        mail_category_class.objects.filter(dynamic_segment_name=old_name).update(
            dynamic_segment_name=new_name
        )

    email_configuration_version_class = apps.get_model(
        "tapir_mail", "EmailConfigurationVersion"
    )
    for version in email_configuration_version_class.objects.all():
        additive = [
            renamed_segments.get(name, name)
            for name in version.dynamic_segments_additive
        ]
        subtractive = [
            renamed_segments.get(name, name)
            for name in version.dynamic_segments_subtractive
        ]
        if (
            additive != version.dynamic_segments_additive
            or subtractive != version.dynamic_segments_subtractive
        ):
            version.dynamic_segments_additive = additive
            version.dynamic_segments_subtractive = subtractive
            version.save()


def forwards(apps, schema):
    rename_segments(apps, RENAMED_SEGMENTS)


def backwards(apps, schema):
    rename_segments(apps, {new: old for old, new in RENAMED_SEGMENTS.items()})


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0141_remove_coopsharetransaction_payment"),
        ("tapir_mail", "0049_emaildispatch_not_before_is_automatic_retry"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
