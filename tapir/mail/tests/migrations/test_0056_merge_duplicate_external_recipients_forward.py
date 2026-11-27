import datetime

from django.utils import timezone
from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestMergeDuplicateExternalRecipientsForward(MigratorTestCase):
    migrate_from = [("tapir_mail", "0055_remove_externalrecipient_secret_key")]
    migrate_to = [("tapir_mail", "0056_merge_duplicate_external_recipients")]

    def prepare(self):
        ExternalRecipient = self.old_state.apps.get_model(
            "tapir_mail", "ExternalRecipient"
        )
        ExternalRecipientConfirmation = self.old_state.apps.get_model(
            "tapir_mail", "ExternalRecipientConfirmation"
        )
        StaticSegment = self.old_state.apps.get_model("tapir_mail", "StaticSegment")
        MailCategory = self.old_state.apps.get_model("tapir_mail", "MailCategory")
        shared_category, duplicate_only_category = [
            MailCategory.objects.create(
                name=name,
                mode="always_on",
                available_for_external_recipients=True,
                static_segment=StaticSegment.objects.create(name=name),
            )
            for name in ["shared", "dup_only"]
        ]

        kept = ExternalRecipient.objects.create(
            id="kept", email="shared@example.com", first_name="Kept"
        )
        duplicate = ExternalRecipient.objects.create(
            id="dup", email="shared@example.com", first_name="Duplicate"
        )
        ExternalRecipient.objects.filter(id="dup").update(
            created_at=timezone.now() + datetime.timedelta(days=1)
        )
        ExternalRecipient.objects.create(
            id="other", email="other@example.com", first_name="Other"
        )
        ExternalRecipientConfirmation.objects.create(
            id="k_shared", external_recipient=kept, mail_category=shared_category
        )
        ExternalRecipientConfirmation.objects.create(
            id="dup_shared",
            external_recipient=duplicate,
            mail_category=shared_category,
        )
        ExternalRecipientConfirmation.objects.create(
            id="dup_only",
            external_recipient=duplicate,
            mail_category=duplicate_only_category,
        )

    def test_forward(self):
        ExternalRecipient = self.new_state.apps.get_model(
            "tapir_mail", "ExternalRecipient"
        )
        ExternalRecipientConfirmation = self.new_state.apps.get_model(
            "tapir_mail", "ExternalRecipientConfirmation"
        )

        self.assertEqual(
            {"kept", "other"},
            set(ExternalRecipient.objects.values_list("id", flat=True)),
        )
        self.assertEqual(
            {("k_shared", "kept"), ("dup_only", "kept")},
            set(
                ExternalRecipientConfirmation.objects.values_list(
                    "id", "external_recipient_id"
                )
            ),
        )
