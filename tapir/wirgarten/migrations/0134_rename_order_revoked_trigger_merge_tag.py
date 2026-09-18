from django.db import migrations
from tapir_mail.models import ReleaseStatus

OLD_TRIGGER_NAME = "Bestellung widerruft"
NEW_TRIGGER_NAME = "Bestellung widerrufen"


def rename_order_revoked_trigger_merge_tag(apps, schema):
    # Fixed the typo in the transactional trigger "Bestellung widerruft" -> "Bestellung widerrufen". See infra#251.

    email_configuration_version_class = apps.get_model(
        "tapir_mail", "EmailConfigurationVersion"
    )

    for email_configuration_version in email_configuration_version_class.objects.filter(
        status__in=[ReleaseStatus.RELEASED, ReleaseStatus.DRAFT]
    ):
        content = email_configuration_version.content
        updated_content = content.replace(
            f"{OLD_TRIGGER_NAME}.", f"{NEW_TRIGGER_NAME}."
        )

        if updated_content != content:
            email_configuration_version.content = updated_content
            email_configuration_version.save()


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0133_rename_coop_membership_only_trigger_merge_tag"),
    ]

    operations = [
        migrations.RunPython(rename_order_revoked_trigger_merge_tag),
    ]
