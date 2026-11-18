from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wirgarten", "0147_pickuplocation_is_home_delivery_optional_coords"),
    ]

    operations = [
        # The values were always correct, only the names were swapped:
        # coords_lon held the latitude and coords_lat the longitude.
        migrations.RenameField(
            model_name="pickuplocation",
            old_name="coords_lon",
            new_name="latitude",
        ),
        migrations.RenameField(
            model_name="pickuplocation",
            old_name="coords_lat",
            new_name="longitude",
        ),
        migrations.AlterField(
            model_name="pickuplocation",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=10,
                max_digits=12,
                null=True,
                verbose_name="Breitengrad",
            ),
        ),
        migrations.AlterField(
            model_name="pickuplocation",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=10,
                max_digits=12,
                null=True,
                verbose_name="Längengrad",
            ),
        ),
    ]
