# Generated by Django 3.2.16 on 2022-11-21 13:16

from django.db import migrations, models
import django.db.models.deletion
import functools
import tapir.core.models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0027_auto_20221109_1136"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="price",
        ),
        migrations.CreateModel(
            name="ProductPrice",
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
                (
                    "price",
                    models.DecimalField(decimal_places=2, editable=False, max_digits=8),
                ),
                ("valid_from", models.DateField(editable=False)),
                (
                    "product",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.producttype",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]