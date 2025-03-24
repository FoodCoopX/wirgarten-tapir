# Generated by Django 3.2.25 on 2025-03-18 12:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("wirgarten", "0046_subscription_notice_period_duration_in_months"),
    ]

    operations = [
        migrations.CreateModel(
            name="NoticePeriod",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("duration_in_months", models.IntegerField()),
                (
                    "growing_period",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="wirgarten.growingperiod",
                    ),
                ),
                (
                    "product_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="wirgarten.producttype",
                    ),
                ),
            ],
        ),
    ]
