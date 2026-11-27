from django.db import migrations
from django.apps.registry import Apps
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models.functions import Lower, Trim


def normalise_email_addresses(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
    for model_name, field_name in [
        ("EmailDispatch", "recipient"),
        ("ExternalRecipient", "email"),
        ("StaticSegmentRecipient", "email"),
    ]:
        apps.get_model("tapir_mail", model_name).objects.update(
            **{field_name: Lower(Trim(field_name))}
        )


class Migration(migrations.Migration):

    dependencies = [
        ("tapir_mail", "0053_registration_recipient_foreign_keys"),
    ]

    operations = [
        migrations.RunPython(normalise_email_addresses, migrations.RunPython.noop),
    ]
