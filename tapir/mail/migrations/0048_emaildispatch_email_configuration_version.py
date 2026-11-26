import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tapir_mail", "0047_auto_20260410_1331"),
    ]

    operations = [
        migrations.AddField(
            model_name="emaildispatch",
            name="email_configuration_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="tapir_mail.emailconfigurationversion",
            ),
        ),
    ]
