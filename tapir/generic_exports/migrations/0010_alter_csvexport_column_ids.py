# Generated by Django 3.2.25 on 2025-03-24 10:56

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("generic_exports", "0009_auto_20250312_1452"),
    ]

    operations = [
        migrations.AlterField(
            model_name="csvexport",
            name="column_ids",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(blank=True, max_length=512),
                blank=True,
                default=list,
                size=None,
            ),
        ),
    ]
