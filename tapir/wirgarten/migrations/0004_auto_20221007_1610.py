# Generated by Django 3.2.16 on 2022-10-07 14:10

from django.db import migrations, models
import functools
import tapir.core.models


class Migration(migrations.Migration):
    dependencies = [
        ("wirgarten", "0003_auto_20221007_1342"),
    ]

    operations = [
        migrations.AlterField(
            model_name="exportedfile",
            name="id",
            field=models.CharField(
                default=functools.partial(tapir.core.models.generate_id, *(), **{}),
                max_length=16,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="growingperiod",
            name="id",
            field=models.CharField(
                default=functools.partial(tapir.core.models.generate_id, *(), **{}),
                max_length=16,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="pickuplocation",
            name="id",
            field=models.CharField(
                default=functools.partial(tapir.core.models.generate_id, *(), **{}),
                max_length=16,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="id",
            field=models.CharField(
                default=functools.partial(tapir.core.models.generate_id, *(), **{}),
                max_length=16,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="productcapacity",
            name="id",
            field=models.CharField(
                default=functools.partial(tapir.core.models.generate_id, *(), **{}),
                max_length=16,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="producttype",
            name="id",
            field=models.CharField(
                default=functools.partial(tapir.core.models.generate_id, *(), **{}),
                max_length=16,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="shareownership",
            name="id",
            field=models.CharField(
                default=functools.partial(tapir.core.models.generate_id, *(), **{}),
                max_length=16,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="id",
            field=models.CharField(
                default=functools.partial(tapir.core.models.generate_id, *(), **{}),
                max_length=16,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="ID",
            ),
        ),
    ]
