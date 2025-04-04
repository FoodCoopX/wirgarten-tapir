# Generated by Django 3.2.25 on 2025-03-11 11:37

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("generic_exports", "0003_auto_20250310_1503"),
    ]

    operations = [
        migrations.AlterField(
            model_name="csvexport",
            name="column_ids",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=512),
                blank=True,
                default=list,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="csvexport",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="csvexport",
            name="email_recipients",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.EmailField(max_length=254),
                blank=True,
                default=list,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="csvexport",
            name="name",
            field=models.CharField(max_length=512, unique=True),
        ),
    ]
