from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def reset_extras_owned_elsewhere(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
    # An address may be owned by only one member: as their main address or as one
    # confirmed extra. Confirmed extras that break this (the address is a main
    # address, or a later confirmation of an already owned address) go back to
    # unconfirmed, and their category registrations are removed.
    Member = apps.get_model("wirgarten", "Member")
    MemberExtraEmail = apps.get_model("wirgarten", "MemberExtraEmail")
    InternalRecipientCategoryRegistration = apps.get_model(
        "tapir_mail", "InternalRecipientCategoryRegistration"
    )

    owned_addresses = set(Member.objects.values_list("email", flat=True))
    extra_ids_to_reset = []
    for extra_email in MemberExtraEmail.objects.filter(
        confirmed_on__isnull=False
    ).order_by("confirmed_on", "id"):
        if extra_email.email in owned_addresses:
            extra_ids_to_reset.append(extra_email.id)
        else:
            owned_addresses.add(extra_email.email)

    InternalRecipientCategoryRegistration.objects.filter(
        member_extra_email_id__in=extra_ids_to_reset
    ).delete()
    MemberExtraEmail.objects.filter(id__in=extra_ids_to_reset).update(confirmed_on=None)


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0157_normalise_email_addresses"),
        ("accounts", "0009_normalise_email_addresses"),
        ("tapir_mail", "0054_normalise_email_addresses"),
    ]

    operations = [
        migrations.RunPython(reset_extras_owned_elsewhere, migrations.RunPython.noop),
    ]
