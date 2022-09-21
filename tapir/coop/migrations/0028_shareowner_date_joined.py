# Generated by Django 3.2.12 on 2022-03-30 11:41

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("coop", "0027_auto_20220317_2100"),
    ]

    operations = [
        migrations.AddField(
            model_name="shareowner",
            name="date_joined",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="date joined"
            ),
        ),
    ]
