# Generated by Django 3.2.18 on 2023-04-13 12:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("log", "0001_initial"),
        ("wirgarten", "0012_auto_20230408_1741"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionChangeLogEntry",
            fields=[
                (
                    "logentry_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="log.logentry",
                    ),
                ),
                (
                    "change_type",
                    models.CharField(
                        choices=[
                            ("ADDED", "Vertragsabschluss"),
                            ("CANCELLED", "Kündigung"),
                            ("RENEWED", "Verlängerung"),
                            ("NOT_RENEWED", "Keine Verlängerung"),
                        ],
                        max_length=32,
                    ),
                ),
                ("subscriptions", models.CharField(max_length=256)),
            ],
            bases=("log.logentry",),
        ),
    ]
