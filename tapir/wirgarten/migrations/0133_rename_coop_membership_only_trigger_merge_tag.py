from django.db import migrations
from tapir_mail.models import ReleaseStatus

OLD_TRIGGER_NAME = "BestellWizard: Nur Geno-Mitgliedschaft"
NEW_TRIGGER_NAME = "BestellWizard: Nur Geno-/Vereinsmitgliedschaft"


def rename_coop_membership_only_trigger_merge_tag(apps, schema):
    # The trigger "BestellWizard: Nur Geno-Mitgliedschaft" was renamed to
    # "BestellWizard: Nur Geno-/Vereinsmitgliedschaft", since it also fires
    # for Verein-only memberships (no product subscriptions ordered), not
    # just Genossenschaft ones. See GitHub issue #1244.

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
        ("wirgarten", "0132_rename_coop_entry_date_merge_tag"),
    ]

    operations = [
        migrations.RunPython(rename_coop_membership_only_trigger_merge_tag),
    ]
