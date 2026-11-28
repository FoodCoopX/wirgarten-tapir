from django.db import migrations
from django.apps.registry import Apps
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def normalise_email_addresses(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
    for model_name in ["CsvExport", "PdfExport"]:
        model = apps.get_model("generic_exports", model_name)
        for export in model.objects.all():
            export.email_recipients = [
                address.strip().lower() for address in export.email_recipients
            ]
            export.save(update_fields=["email_recipients"])


class Migration(migrations.Migration):

    dependencies = [
        ("generic_exports", "0013_alter_automated_export_cycle_choices"),
    ]

    operations = [
        migrations.RunPython(normalise_email_addresses, migrations.RunPython.noop),
    ]
