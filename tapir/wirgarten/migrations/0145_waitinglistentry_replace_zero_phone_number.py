from django.db import migrations


def replace_zero_phone_numbers(apps, schema_editor):
    apps.get_model("wirgarten", "WaitingListEntry").objects.filter(
        phone_number="0"
    ).update(phone_number="")


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0144_waitinglistentry_pseudonym"),
    ]

    operations = [
        migrations.RunPython(replace_zero_phone_numbers, migrations.RunPython.noop),
    ]
