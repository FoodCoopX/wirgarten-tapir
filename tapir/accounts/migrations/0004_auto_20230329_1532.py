# Generated by Django 3.2.18 on 2023-03-29 13:32

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_emailchangerequest"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tapiruser",
            name="email",
            field=models.CharField(blank=True, max_length=150, verbose_name="Email"),
        ),
        migrations.AlterField(
            model_name="tapiruser",
            name="phone_number",
            field=phonenumber_field.modelfields.PhoneNumberField(
                blank=True,
                max_length=128,
                null=True,
                region=None,
                verbose_name="Phone number",
            ),
        ),
    ]