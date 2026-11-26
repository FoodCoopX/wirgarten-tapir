from django.db import migrations

ALWAYS_ON = "always_on"
OPTIONAL_DEFAULT_ON = "optional_default_on"


def backfill_category_registrations(apps, schema_editor):
    MemberExtraEmail = apps.get_model("wirgarten", "MemberExtraEmail")
    MailCategory = apps.get_model("tapir_mail", "MailCategory")
    InternalRecipientCategoryRegistration = apps.get_model(
        "tapir_mail", "InternalRecipientCategoryRegistration"
    )

    mail_categories = list(MailCategory.objects.exclude(dynamic_segment_name=""))
    member_registration_states = {
        (registration.member_id, registration.mail_category_id): (
            registration.is_registered
        )
        for registration in InternalRecipientCategoryRegistration.objects.filter(
            member__isnull=False
        )
    }

    InternalRecipientCategoryRegistration.objects.bulk_create(
        [
            InternalRecipientCategoryRegistration(
                member_extra_email=extra_email,
                mail_category=mail_category,
                is_registered=mail_category.mode == ALWAYS_ON
                or member_registration_states.get(
                    (extra_email.member_id, mail_category.id),
                    mail_category.mode == OPTIONAL_DEFAULT_ON,
                ),
            )
            for extra_email in MemberExtraEmail.objects.filter(
                confirmed_on__isnull=False
            )
            for mail_category in mail_categories
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0154_member_extra_email_receives_direct_mails"),
        ("tapir_mail", "0053_registration_recipient_foreign_keys"),
    ]

    operations = [
        migrations.RunPython(
            code=backfill_category_registrations,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
