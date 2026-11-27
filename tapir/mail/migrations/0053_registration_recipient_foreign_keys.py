import django.db.models.deletion
from django.db import migrations, models


def link_registrations_to_members(apps, schema_editor):
    Member = apps.get_model("wirgarten", "Member")
    InternalRecipientCategoryRegistration = apps.get_model(
        "tapir_mail", "InternalRecipientCategoryRegistration"
    )

    member_ids = set(Member.objects.values_list("id", flat=True))
    registrations_to_update = []
    registration_ids_to_delete = []
    seen_keys = set()
    for registration in InternalRecipientCategoryRegistration.objects.order_by(
        "-created_at"
    ):
        key = (registration.mail_category_id, registration.internal_recipient_id)
        if registration.internal_recipient_id not in member_ids or key in seen_keys:
            registration_ids_to_delete.append(registration.id)
            continue
        seen_keys.add(key)
        registration.member_id = registration.internal_recipient_id
        registrations_to_update.append(registration)

    InternalRecipientCategoryRegistration.objects.filter(
        id__in=registration_ids_to_delete
    ).delete()
    InternalRecipientCategoryRegistration.objects.bulk_update(
        registrations_to_update, fields=["member"]
    )


def copy_recipient_ids_back(apps, schema_editor):
    InternalRecipientCategoryRegistration = apps.get_model(
        "tapir_mail", "InternalRecipientCategoryRegistration"
    )

    registrations = list(InternalRecipientCategoryRegistration.objects.all())
    for registration in registrations:
        registration.internal_recipient_id = (
            registration.member_id or registration.member_extra_email_id
        )
    InternalRecipientCategoryRegistration.objects.bulk_update(
        registrations, fields=["internal_recipient_id"]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tapir_mail", "0052_stable_trigger_ids"),
        ("wirgarten", "0154_member_extra_email_receives_direct_mails"),
    ]

    operations = [
        migrations.AddField(
            model_name="internalrecipientcategoryregistration",
            name="member",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="wirgarten.member",
            ),
        ),
        migrations.AddField(
            model_name="internalrecipientcategoryregistration",
            name="member_extra_email",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="wirgarten.memberextraemail",
            ),
        ),
        # Nullable so that reverting the RemoveField below works on existing rows.
        migrations.AlterField(
            model_name="internalrecipientcategoryregistration",
            name="internal_recipient_id",
            field=models.CharField(max_length=10, null=True),
        ),
        migrations.RunPython(
            code=link_registrations_to_members,
            reverse_code=copy_recipient_ids_back,
        ),
        migrations.RemoveField(
            model_name="internalrecipientcategoryregistration",
            name="internal_recipient_id",
        ),
        migrations.AddConstraint(
            model_name="internalrecipientcategoryregistration",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("member__isnull", False), ("member_extra_email__isnull", True)
                    ),
                    models.Q(
                        ("member__isnull", True), ("member_extra_email__isnull", False)
                    ),
                    _connector="OR",
                ),
                name="registration_has_exactly_one_recipient",
            ),
        ),
        migrations.AddConstraint(
            model_name="internalrecipientcategoryregistration",
            constraint=models.UniqueConstraint(
                fields=("mail_category", "member"),
                name="unique_member_registration_per_category",
            ),
        ),
        migrations.AddConstraint(
            model_name="internalrecipientcategoryregistration",
            constraint=models.UniqueConstraint(
                fields=("mail_category", "member_extra_email"),
                name="unique_member_extra_email_registration_per_category",
            ),
        ),
    ]
