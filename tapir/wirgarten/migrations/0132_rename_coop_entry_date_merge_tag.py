from django.db import migrations
from tapir_mail.models import ReleaseStatus

OLD_TOKEN_LABEL = "Beitrittsdatum in der Genossenschaft"
NEW_TOKEN_LABEL = "Beitrittsdatum Geno/Verein"

# Every transactional trigger that merges TOKENS_COOP_ENTRY into its tokens (see tapirmail.py)
TRIGGER_NAMES = [
    "BestellWizard: Mitgliedschaft + Ernteanteile",
    "BestellWizard: Nur Geno-Mitgliedschaft",
    "Bestellung durch Warteliste-Link abgeschlossen",
]


def rename_coop_entry_date_merge_tag(apps, schema):
    # The token "Beitrittsdatum in der Genossenschaft" was renamed to "Beitrittsdatum Geno/Verein",
    # since it is also used when the general config's organisation type is set to "Verein".

    email_configuration_version_class = apps.get_model(
        "tapir_mail", "EmailConfigurationVersion"
    )

    for email_configuration_version in email_configuration_version_class.objects.filter(
        status__in=[ReleaseStatus.RELEASED, ReleaseStatus.DRAFT]
    ):
        content = email_configuration_version.content
        updated_content = content
        for trigger_name in TRIGGER_NAMES:
            updated_content = updated_content.replace(
                f"{trigger_name}.{OLD_TOKEN_LABEL}",
                f"{trigger_name}.{NEW_TOKEN_LABEL}",
            )

        if updated_content != content:
            email_configuration_version.content = updated_content
            email_configuration_version.save()


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0131_rename_trial_cancellation_merge_tag"),
    ]

    operations = [
        migrations.RunPython(rename_coop_entry_date_merge_tag),
    ]
