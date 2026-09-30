from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wirgarten", "0133_rename_coop_membership_only_trigger_merge_tag"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pickuplocation",
            name="info",
            field=models.CharField(
                blank=True, max_length=3000, verbose_name="Additional info"
            ),
        ),
        migrations.AlterField(
            model_name="pickuplocation",
            name="route_info",
            field=models.CharField(
                blank=True, max_length=3000, verbose_name="Driver/Route info"
            ),
        ),
    ]
