# Generated by Django 3.2.25 on 2025-03-10 14:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("generic_exports", "0002_auto_20250310_1446"),
    ]

    operations = [
        migrations.RenameField(
            model_name="csvexport",
            old_name="columns",
            new_name="column_ids",
        ),
        migrations.RenameField(
            model_name="csvexport",
            old_name="dataset_id",
            new_name="export_segment_id",
        ),
    ]
