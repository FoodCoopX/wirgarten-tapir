# Generated by Django 3.1.13 on 2021-10-22 07:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shifts", "0028_auto_20211022_0856"),
    ]

    operations = [
        migrations.RenameField(
            model_name="shifttemplate",
            old_name="required_attendances",
            new_name="num_required_attendances",
        ),
        migrations.RemoveField(
            model_name="shift",
            name="required_attendances",
        ),
        migrations.AddField(
            model_name="shift",
            name="num_required_attendances",
            field=models.IntegerField(default=3, null=True),
        ),
    ]
