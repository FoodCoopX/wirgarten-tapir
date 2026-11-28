from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def merge_duplicate_external_recipients(
    apps: Apps, schema_editor: BaseDatabaseSchemaEditor
):
    ExternalRecipient = apps.get_model("tapir_mail", "ExternalRecipient")
    ExternalRecipientConfirmation = apps.get_model(
        "tapir_mail", "ExternalRecipientConfirmation"
    )

    kept_by_email = {}
    for external_recipient in ExternalRecipient.objects.order_by("created_at", "id"):
        kept = kept_by_email.setdefault(external_recipient.email, external_recipient)
        if kept == external_recipient:
            continue

        ExternalRecipientConfirmation.objects.filter(
            external_recipient=external_recipient
        ).exclude(
            mail_category_id__in=ExternalRecipientConfirmation.objects.filter(
                external_recipient=kept
            ).values("mail_category_id")
        ).update(
            external_recipient=kept
        )
        external_recipient.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tapir_mail", "0055_remove_externalrecipient_secret_key"),
    ]

    operations = [
        migrations.RunPython(
            merge_duplicate_external_recipients, migrations.RunPython.noop
        ),
    ]
