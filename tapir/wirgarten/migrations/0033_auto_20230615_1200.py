# Generated by Django 3.2.18 on 2023-06-15 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0032_auto_20230615_1158"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="payment",
            name="unique_mandate_ref_date",
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(
                fields=("mandate_ref", "due_date", "type"),
                name="unique_mandate_ref_date",
            ),
        ),
    ]
