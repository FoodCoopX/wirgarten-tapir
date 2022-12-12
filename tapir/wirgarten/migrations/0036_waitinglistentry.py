# Generated by Django 3.2.16 on 2022-12-02 11:36

from django.db import migrations, models
import django.db.models.deletion
import functools
import tapir.core.models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0035_receivedcoopshareslogentry"),
    ]

    operations = [
        migrations.CreateModel(
            name="WaitingListEntry",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("first_name", models.CharField(max_length=256)),
                ("last_name", models.CharField(max_length=256)),
                ("email", models.CharField(max_length=256)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("HARVEST_SHARES", "Ernteanteile"),
                            ("COOP_SHARES", "Genossenschaftsanteile"),
                        ],
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("privacy_consent", models.DateTimeField()),
                (
                    "member",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.member",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]