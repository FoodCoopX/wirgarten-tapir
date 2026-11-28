from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tapir_mail", "0048_emaildispatch_email_configuration_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="emaildispatch",
            name="not_before",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="emaildispatch",
            name="is_automatic_retry",
            field=models.BooleanField(default=False),
        ),
    ]
