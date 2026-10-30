from django.db import migrations

# The ended-text default of the bidding round used a Markdown link, which is rendered
# literally (the texts are rendered as raw HTML). Replace the default with an HTML link,
# but only for rows that still have the unchanged default, so admin edits are kept.
KEY = "wirgarten.bidding_round.public.ended_text"

OLD_TEXT = (
    "Die aktuelle Beitragsrunde ist beendet. Du kannst jederzeit Mitglied werden – über "
    "unseren [Bestell-Wizard](/bestell_wizard/bestell_wizard_mobile) gelangst du direkt zur "
    "Anmeldung. Wir freuen uns auf dich!"
)
NEW_TEXT = (
    "Die aktuelle Beitragsrunde ist beendet. Du kannst jederzeit Mitglied werden – über "
    'unseren <a href="/bestell_wizard/bestell_wizard_mobile">Bestell-Wizard</a> gelangst du '
    "direkt zur Anmeldung. Wir freuen uns auf dich!"
)


def to_html(apps, schema_editor):
    TapirParameter = apps.get_model("configuration", "TapirParameter")
    TapirParameter.objects.filter(key=KEY, value=OLD_TEXT).update(value=NEW_TEXT)


def to_markdown(apps, schema_editor):
    TapirParameter = apps.get_model("configuration", "TapirParameter")
    TapirParameter.objects.filter(key=KEY, value=NEW_TEXT).update(value=OLD_TEXT)


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0007_tapirparameter_remove_field_required"),
    ]

    operations = [
        migrations.RunPython(to_html, to_markdown),
    ]
