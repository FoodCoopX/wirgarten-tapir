# Generated by Django 3.2.25 on 2025-03-26 11:14

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "deliveries",
            "0003_deliverydayadjustment_no_duplicate_week_by_growing_period",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="deliverydayadjustment",
            name="adjusted_weekday",
            field=models.IntegerField(
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(6),
                ]
            ),
        ),
    ]
