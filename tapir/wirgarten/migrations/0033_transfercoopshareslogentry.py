# Generated by Django 3.2.16 on 2022-11-27 17:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("log", "0001_initial"),
        ("wirgarten", "0032_auto_20221127_1418"),
    ]

    operations = [
        migrations.CreateModel(
            name="TransferCoopSharesLogEntry",
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
                ("quantity", models.PositiveSmallIntegerField()),
                (
                    "target_member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.member",
                    ),
                ),
            ],
            bases=("log.logentry",),
        ),
    ]
