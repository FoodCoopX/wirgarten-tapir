import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("tapir_mail", "0050_email_dispatch_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailtemplate",
            name="template_type",
            field=models.CharField(
                choices=[
                    ("start", "Start-Vorlage"),
                    ("layout", "Layout-Vorlage"),
                ],
                default="start",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="emailtemplate",
            name="is_default_layout",
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="emailtemplate",
            constraint=models.UniqueConstraint(
                condition=Q(is_default_layout=True),
                fields=("is_default_layout",),
                name="unique_default_layout_template",
            ),
        ),
        migrations.AddField(
            model_name="emailconfigurationversion",
            name="layout_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="versions_using_layout",
                to="tapir_mail.emailtemplate",
            ),
        ),
        migrations.AddField(
            model_name="emailconfigurationversion",
            name="layout_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
