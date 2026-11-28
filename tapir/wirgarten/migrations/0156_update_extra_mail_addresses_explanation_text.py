from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

KEY = "wirgarten.emails.explanation_text_extra_mail_addresses"

OLD_DEFAULT = """<p>
        Du kannst hier zusätzliche E-Mail-Adressen hinzufügen. Alle Mailings werden dann nach der Bestätigung der neuen E-Mail-Adresse auch an diese versendet. An die neue E-Mail-Adresse wird ein Bestätigungslink versendet.
</p>"""

NEW_DEFAULT = """<p>
        Du kannst hier zusätzliche E-Mail-Adressen hinzufügen. An die neue E-Mail-Adresse wird ein Bestätigungslink versendet.
</p>
<p>
        Wenn die Adresse auch persönliche Mails erhält, bekommt sie nach der Bestätigung eine Kopie aller Mails an deine Hauptadresse (Verträge, Abholung, Rundmails an alle Mitglieder) und übernimmt deine Anmeldungen zu Mail-Kategorien und Mailinglisten. Sonst erhält sie nur die Mails der Kategorien und Mailinglisten, für die sie selbst angemeldet ist.
</p>
<p>
        Die Anmeldungen werden nur bei der ersten Bestätigung übernommen. Danach verwaltet die Adresse ihre Abos selbst, über einen Link, den du ihr mit "Link senden" schicken kannst. Wenn du persönliche Mails erst später einschaltest, werden keine Anmeldungen übernommen.
</p>"""


def replace_unchanged_default(apps: Apps, old_value: str, new_value: str):
    TapirParameter = apps.get_model("configuration", "TapirParameter")
    parameter = TapirParameter.objects.filter(key=KEY).first()
    if parameter is None or parameter.value.split() != old_value.split():
        return
    parameter.value = new_value
    parameter.save()


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
    replace_unchanged_default(apps=apps, old_value=OLD_DEFAULT, new_value=NEW_DEFAULT)


def backwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
    replace_unchanged_default(apps=apps, old_value=NEW_DEFAULT, new_value=OLD_DEFAULT)


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0155_backfill_member_extra_email_category_registrations"),
        ("configuration", "0007_tapirparameter_remove_field_required"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
