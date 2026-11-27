from django.db import migrations
from django.apps.registry import Apps
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models.functions import Lower, Trim


def normalise_email_addresses(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
    for model_name, field_name in [
        ("TapirUser", "email"),
        ("EmailChangeRequest", "new_email"),
    ]:
        apps.get_model("accounts", model_name).objects.update(
            **{field_name: Lower(Trim(field_name))}
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_alter_tapiruser_birthdate_alter_tapiruser_city_and_more"),
    ]

    operations = [
        migrations.RunPython(normalise_email_addresses, migrations.RunPython.noop),
    ]
