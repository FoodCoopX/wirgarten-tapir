# Generated by Django 3.2.16 on 2022-11-21 13:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0028_auto_20221121_1416"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productprice",
            name="product",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.product",
            ),
        ),
    ]
