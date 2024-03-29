# Generated by Django 3.2.18 on 2023-08-03 14:19

from django.db import migrations, models
import functools
import tapir.core.models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0036_auto_20230726_1541"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScheduledTask",
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
                ("task_function", models.CharField(max_length=255)),
                ("task_args", models.JSONField(blank=True, default=list)),
                ("task_kwargs", models.JSONField(blank=True, default=dict)),
                ("eta", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("IN_PROGRESS", "In Progress"),
                            ("DONE", "Done"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
