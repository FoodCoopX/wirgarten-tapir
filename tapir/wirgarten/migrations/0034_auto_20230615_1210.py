# Generated by Django 3.2.18 on 2023-06-15 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0033_auto_20230615_1200"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymenttransaction",
            name="type",
            field=models.CharField(max_length=32, null=True),
        ),
    ]
