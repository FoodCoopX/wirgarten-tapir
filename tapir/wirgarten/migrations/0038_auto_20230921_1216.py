# Generated by Django 3.2.18 on 2023-09-21 10:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0037_scheduledtask"),
    ]

    operations = [
        migrations.AddField(
            model_name="producttype",
            name="contract_link",
            field=models.CharField(
                blank=True,
                max_length=512,
                null=True,
                verbose_name="Link zu den Vertragsgrundsätzen",
            ),
        ),
        migrations.AddField(
            model_name="producttype",
            name="icon_link",
            field=models.CharField(
                blank=True, max_length=512, null=True, verbose_name="Link zum Icon"
            ),
        ),
        migrations.AddField(
            model_name="producttype",
            name="single_subscription_only",
            field=models.BooleanField(
                default=False, verbose_name="Nur Einzelabonnement erlaubt"
            ),
        ),
    ]
