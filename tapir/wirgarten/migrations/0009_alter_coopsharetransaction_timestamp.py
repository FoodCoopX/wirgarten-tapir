# Generated by Django 3.2.18 on 2023-04-06 15:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0008_auto_20230330_1418"),
    ]

    operations = [
        migrations.AlterField(
            model_name="coopsharetransaction",
            name="timestamp",
            field=models.DateTimeField(auto_now=True),
        ),
    ]