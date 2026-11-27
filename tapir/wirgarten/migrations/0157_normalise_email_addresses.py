from django.db import migrations
from django.apps.registry import Apps
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models.functions import Lower, Trim


def normalise_email_addresses(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
    for model_name, field_name in [
        ("WaitingListEntry", "email"),
        ("MemberExtraEmail", "email"),
        ("MemberExtraEmailCreatedLogEntry", "email"),
        ("MemberExtraEmailDeletedLogEntry", "email"),
        ("MemberExtraEmailConfirmedLogEntry", "email"),
    ]:
        apps.get_model("wirgarten", model_name).objects.update(
            **{field_name: Lower(Trim(field_name))}
        )


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0156_update_extra_mail_addresses_explanation_text"),
    ]

    operations = [
        migrations.RunPython(normalise_email_addresses, migrations.RunPython.noop),
    ]
