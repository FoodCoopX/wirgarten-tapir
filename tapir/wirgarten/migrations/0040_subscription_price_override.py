# Generated by Django 3.2.23 on 2024-01-09 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0039_coopsharetransaction_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="price_override",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True
            ),
        ),
    ]
